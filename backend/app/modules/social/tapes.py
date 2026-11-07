import dataclasses
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_opaque_token, new_opaque_token
from app.modules.catalog.public import get_songs
from app.modules.social.models import InviteClaim, Tape, TapeInvite, TapeMember, TapeTrack
from app.modules.social.schemas import InviteIn, OrderIn, TapeIn, TapePatch, TrackIn
from app.modules.users.public import get_display_names

log = logging.getLogger(__name__)


def _not_found() -> AppError:
    return AppError(404, "tape_not_found", "Casete no encontrado")


async def _is_member(session: AsyncSession, tape_id: UUID, user_id: UUID) -> bool:
    query = select(TapeMember.user_id).where(TapeMember.tape_id == tape_id, TapeMember.user_id == user_id)
    return await session.scalar(query) is not None


async def _load_as_member(session: AsyncSession, user: CurrentUser, tape_id: UUID) -> Tape:
    tape = await session.get(Tape, tape_id)
    if tape is None:
        raise _not_found()
    if not await _is_member(session, tape_id, user.id):
        raise AppError(403, "not_a_member", "No eres miembro de este casete")
    return tape


async def _lock(session: AsyncSession, tape_id: UUID) -> Tape:
    """Serializa las escrituras de un casete: límites, orden e invitaciones."""
    query = select(Tape).where(Tape.id == tape_id).with_for_update().execution_options(populate_existing=True)
    tape = await session.scalar(query)
    if tape is None:
        raise _not_found()
    return tape


async def _lock_as_member(session: AsyncSession, user: CurrentUser, tape_id: UUID) -> Tape:
    tape = await _lock(session, tape_id)
    if not await _is_member(session, tape_id, user.id):
        raise AppError(403, "not_a_member", "No eres miembro de este casete")
    return tape


def _require_creator(tape: Tape, user: CurrentUser) -> None:
    if tape.creator_id != user.id:
        raise AppError(403, "not_the_creator", "Solo quien creó el casete puede hacer esto")


async def create(session: AsyncSession, user: CurrentUser, data: TapeIn) -> Tape:
    tape = Tape(title=data.title, color=data.color, creator_id=user.id)
    session.add(tape)
    await session.flush()
    session.add(TapeMember(tape_id=tape.id, user_id=user.id))
    await session.commit()
    return tape


async def list_mine(session: AsyncSession, user: CurrentUser) -> list[dict]:
    other = aliased(TapeMember)
    members = select(func.count()).select_from(other).where(other.tape_id == Tape.id).correlate(Tape).scalar_subquery()
    tracks = (
        select(func.count()).select_from(TapeTrack).where(TapeTrack.tape_id == Tape.id).correlate(Tape).scalar_subquery()
    )
    query = (
        select(Tape, members, tracks)
        .join(TapeMember, TapeMember.tape_id == Tape.id)
        .where(TapeMember.user_id == user.id)
        .order_by(Tape.created_at.desc())
    )
    return [
        {
            "id": tape.id,
            "title": tape.title,
            "color": tape.color,
            "is_creator": tape.creator_id == user.id,
            "member_count": member_count,
            "track_count": track_count,
            "max_tracks": get_settings().TAPE_MAX_TRACKS,
            "created_at": tape.created_at,
        }
        for tape, member_count, track_count in (await session.execute(query)).all()
    ]


def _side(position: int) -> str:
    half = (get_settings().TAPE_MAX_TRACKS + 1) // 2
    return "A" if position <= half else "B"


def _cache(summary) -> dict:
    return jsonable_encoder(dataclasses.asdict(summary))


async def _resolve_songs(session: AsyncSession, rows: list[TapeTrack]) -> tuple[dict[UUID, dict], bool]:
    """Datos actuales de cada pista, o los de la caché si catálogo falla o ya no la tiene."""
    ids = [r.song_id for r in rows]
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    try:
        found = await get_songs(ids)
    except Exception:
        log.warning("Catálogo no disponible: casete con metadatos en caché")
        return {r.song_id: r.metadata_cache for r in rows}, True
    songs = {}
    for row in rows:
        summary = found.get(row.song_id)
        if summary is None:
            songs[row.song_id] = {**row.metadata_cache, "available": False}
            continue
        songs[row.song_id] = _cache(summary)
        if songs[row.song_id] != row.metadata_cache:
            row.metadata_cache = songs[row.song_id]
    await session.commit()
    return songs, False


async def detail(session: AsyncSession, user: CurrentUser, tape_id: UUID) -> dict:
    tape = await _load_as_member(session, user, tape_id)
    query = select(TapeTrack).where(TapeTrack.tape_id == tape_id).order_by(TapeTrack.position)
    rows = list((await session.execute(query)).scalars())
    query = select(TapeMember).where(TapeMember.tape_id == tape_id).order_by(TapeMember.joined_at)
    members = list((await session.execute(query)).scalars())
    invites = []
    if tape.creator_id == user.id:
        query = (
            select(TapeInvite)
            .where(TapeInvite.tape_id == tape_id, TapeInvite.revoked_at.is_(None))
            .order_by(TapeInvite.created_at.desc())
        )
        invites = list((await session.execute(query)).scalars())
    songs, degraded = await _resolve_songs(session, rows)
    names = await get_display_names(list({m.user_id for m in members} | {r.added_by for r in rows}))
    return {
        "id": tape.id,
        "title": tape.title,
        "color": tape.color,
        "creator_id": tape.creator_id,
        "is_creator": tape.creator_id == user.id,
        "version": tape.version,
        "created_at": tape.created_at,
        "max_tracks": get_settings().TAPE_MAX_TRACKS,
        "max_members": get_settings().TAPE_MAX_MEMBERS,
        "degraded": degraded,
        "members": [{"user_id": m.user_id, "name": names.get(m.user_id), "joined_at": m.joined_at} for m in members],
        "tracks": [
            {
                "id": r.id,
                "position": r.position,
                "side": _side(r.position),
                "song": songs[r.song_id],
                "added_by": r.added_by,
                "added_by_name": names.get(r.added_by),
                "dedication": r.dedication,
                "can_remove": user.id in (r.added_by, tape.creator_id),
            }
            for r in rows
        ],
        "invites": [
            {"id": i.id, "expires_at": i.expires_at, "max_uses": i.max_uses, "uses": i.uses} for i in invites
        ],
    }


async def update_tape(session: AsyncSession, user: CurrentUser, tape_id: UUID, data: TapePatch) -> dict:
    tape = await _lock_as_member(session, user, tape_id)
    _require_creator(tape, user)
    for name, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(tape, name, value)
    await session.commit()
    return {"id": tape.id, "title": tape.title, "color": tape.color}


async def delete_tape(session: AsyncSession, user: CurrentUser, tape_id: UUID) -> None:
    tape = await _lock(session, tape_id)
    _require_creator(tape, user)
    await session.delete(tape)
    await session.commit()


async def add_track(session: AsyncSession, user: CurrentUser, tape_id: UUID, data: TrackIn) -> TapeTrack:
    # Catálogo va primero: no se le llama con la fila del casete bloqueada.
    try:
        songs = await get_songs([data.song_id])
    except Exception as exc:
        raise AppError(503, "catalog_unavailable", "El catálogo no responde. Intenta de nuevo.") from exc
    summary = songs.get(data.song_id)
    if summary is None:
        raise AppError(404, "song_not_found", "Canción no encontrada")
    tape = await _lock_as_member(session, user, tape_id)
    if not summary.available:
        raise AppError(409, "song_unavailable", "Esta canción ya no está disponible")
    query = select(TapeTrack.song_id).where(TapeTrack.tape_id == tape_id)
    present = list((await session.execute(query)).scalars())
    if data.song_id in present:
        raise AppError(409, "song_already_in_tape", "Esta canción ya está en el casete")
    if len(present) >= get_settings().TAPE_MAX_TRACKS:
        raise AppError(409, "tape_full", "El casete ya está lleno")
    track = TapeTrack(
        tape_id=tape_id,
        song_id=data.song_id,
        added_by=user.id,
        position=len(present) + 1,
        dedication=(data.dedication or "").strip() or None,
        metadata_cache=_cache(summary),
    )
    session.add(track)
    tape.version += 1
    await session.commit()
    return track


async def remove_track(session: AsyncSession, user: CurrentUser, tape_id: UUID, track_id: UUID) -> None:
    tape = await _lock_as_member(session, user, tape_id)
    track = await session.get(TapeTrack, track_id)
    if track is None or track.tape_id != tape_id:
        raise AppError(404, "track_not_found", "Esa pista no está en el casete")
    if user.id not in (track.added_by, tape.creator_id):
        raise AppError(403, "forbidden", "Solo quien la agregó o quien creó el casete puede quitarla")
    position = track.position
    await session.delete(track)
    await session.flush()
    await session.execute(
        update(TapeTrack)
        .where(TapeTrack.tape_id == tape_id, TapeTrack.position > position)
        .values(position=TapeTrack.position - 1)
    )
    tape.version += 1
    await session.commit()


async def reorder(session: AsyncSession, user: CurrentUser, tape_id: UUID, data: OrderIn) -> int:
    tape = await _lock_as_member(session, user, tape_id)
    if tape.version != data.version:
        raise AppError(409, "tape_version_conflict", "Alguien cambió el casete. Recarga para ver el orden nuevo.")
    rows = list((await session.execute(select(TapeTrack).where(TapeTrack.tape_id == tape_id))).scalars())
    by_id = {r.id: r for r in rows}
    if len(data.track_ids) != len(rows) or set(data.track_ids) != set(by_id):
        raise AppError(422, "invalid_order", "El orden debe incluir cada pista del casete una vez")
    for position, track_id in enumerate(data.track_ids, start=1):
        by_id[track_id].position = position
    tape.version += 1
    version = tape.version
    await session.commit()
    return version


async def create_invite(session: AsyncSession, user: CurrentUser, tape_id: UUID, data: InviteIn) -> dict:
    await _load_as_member(session, user, tape_id)
    token = new_opaque_token()
    expires_at = None
    if data.expires_in_hours is not None:
        expires_at = datetime.now(UTC) + timedelta(hours=data.expires_in_hours)
    invite = TapeInvite(
        tape_id=tape_id,
        token_hash=hash_opaque_token(token),
        created_by=user.id,
        expires_at=expires_at,
        max_uses=data.max_uses,
    )
    session.add(invite)
    await session.commit()
    return {"id": invite.id, "token": token, "expires_at": expires_at, "max_uses": data.max_uses}


async def revoke_invite(session: AsyncSession, user: CurrentUser, tape_id: UUID, invite_id: UUID) -> None:
    tape = await _lock_as_member(session, user, tape_id)
    _require_creator(tape, user)
    invite = await session.get(TapeInvite, invite_id)
    if invite is None or invite.tape_id != tape_id:
        raise AppError(404, "invite_not_found", "Enlace no encontrado")
    invite.revoked_at = datetime.now(UTC)
    await session.commit()


async def _invite_by_token(session: AsyncSession, token: str) -> TapeInvite:
    invite = await session.scalar(select(TapeInvite).where(TapeInvite.token_hash == hash_opaque_token(token)))
    if invite is None:
        raise AppError(404, "invite_not_found", "Este enlace no existe")
    return invite


def _require_usable(invite: TapeInvite) -> None:
    if invite.revoked_at is not None:
        raise AppError(410, "invite_revoked", "Este enlace ya no está activo")
    if invite.expires_at is not None and invite.expires_at <= datetime.now(UTC):
        raise AppError(410, "invite_expired", "Este enlace ya caducó")
    if invite.uses >= invite.max_uses:
        raise AppError(409, "invite_exhausted", "Este enlace ya se usó por completo")


async def preview(session: AsyncSession, user: CurrentUser, token: str) -> dict:
    invite = await _invite_by_token(session, token)
    tape = await session.get(Tape, invite.tape_id)
    member = await _is_member(session, tape.id, user.id)
    if not member:
        _require_usable(invite)
        statement = insert(InviteClaim).values(invite_id=invite.id, user_id=user.id, status="pending")
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[InviteClaim.invite_id, InviteClaim.user_id],
                set_={"status": "pending"},
                where=InviteClaim.status == "dismissed",
            )
        )
    title, color, created_by, tape_id = tape.title, tape.color, invite.created_by, tape.id
    await session.commit()
    names = await get_display_names([created_by])
    return {
        "title": title,
        "color": color,
        "inviter": names.get(created_by),
        "already_member": member,
        "tape_id": tape_id if member else None,
    }


async def _set_claim(session: AsyncSession, invite_id: UUID, user_id: UUID, status: str) -> None:
    statement = insert(InviteClaim).values(invite_id=invite_id, user_id=user_id, status=status)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[InviteClaim.invite_id, InviteClaim.user_id],
            set_={"status": status},
            where=InviteClaim.status != "joined",
        )
    )


async def _join(session: AsyncSession, user: CurrentUser, invite_id: UUID, tape_id: UUID) -> dict:
    await _lock(session, tape_id)
    query = select(TapeInvite).where(TapeInvite.id == invite_id).execution_options(populate_existing=True)
    invite = await session.scalar(query)
    joined = False
    if not await _is_member(session, tape_id, user.id):
        _require_usable(invite)
        count = select(func.count()).select_from(TapeMember).where(TapeMember.tape_id == tape_id)
        if await session.scalar(count) >= get_settings().TAPE_MAX_MEMBERS:
            raise AppError(409, "tape_full_members", "Este casete ya tiene todos sus miembros")
        session.add(TapeMember(tape_id=tape_id, user_id=user.id))
        invite.uses += 1
        joined = True
    await _set_claim(session, invite_id, user.id, "joined")
    await session.commit()
    return {"tape_id": tape_id, "joined": joined}


async def join_by_token(session: AsyncSession, user: CurrentUser, token: str) -> dict:
    invite = await _invite_by_token(session, token)
    return await _join(session, user, invite.id, invite.tape_id)


async def dismiss_by_token(session: AsyncSession, user: CurrentUser, token: str) -> None:
    invite = await _invite_by_token(session, token)
    await _set_claim(session, invite.id, user.id, "dismissed")
    await session.commit()


async def _own_claim(session: AsyncSession, user: CurrentUser, invite_id: UUID) -> TapeInvite:
    query = (
        select(TapeInvite)
        .join(InviteClaim, InviteClaim.invite_id == TapeInvite.id)
        .where(TapeInvite.id == invite_id, InviteClaim.user_id == user.id, InviteClaim.status == "pending")
    )
    invite = await session.scalar(query)
    if invite is None:
        raise AppError(404, "invite_not_found", "No tienes esta invitación pendiente")
    return invite


async def join_by_claim(session: AsyncSession, user: CurrentUser, invite_id: UUID) -> dict:
    invite = await _own_claim(session, user, invite_id)
    return await _join(session, user, invite.id, invite.tape_id)


async def dismiss_by_claim(session: AsyncSession, user: CurrentUser, invite_id: UUID) -> None:
    await _own_claim(session, user, invite_id)
    await _set_claim(session, invite_id, user.id, "dismissed")
    await session.commit()


async def pending_invites(session: AsyncSession, user: CurrentUser) -> list[dict]:
    """Solo las que aún se pueden aceptar. El token no se guarda: se actúa por `invite_id`."""
    member = exists().where(TapeMember.tape_id == Tape.id, TapeMember.user_id == user.id)
    query = (
        select(TapeInvite, Tape)
        .join(InviteClaim, InviteClaim.invite_id == TapeInvite.id)
        .join(Tape, Tape.id == TapeInvite.tape_id)
        .where(
            InviteClaim.user_id == user.id,
            InviteClaim.status == "pending",
            TapeInvite.revoked_at.is_(None),
            or_(TapeInvite.expires_at.is_(None), TapeInvite.expires_at > func.now()),
            TapeInvite.uses < TapeInvite.max_uses,
            ~member,
        )
        .order_by(TapeInvite.created_at.desc())
    )
    rows = (await session.execute(query)).all()
    items = [
        {
            "invite_id": invite.id,
            "tape_id": tape.id,
            "title": tape.title,
            "color": tape.color,
            "created_by": invite.created_by,
            "expires_at": invite.expires_at,
        }
        for invite, tape in rows
    ]
    await session.commit()
    names = await get_display_names(list({i["created_by"] for i in items}))
    return [{**i, "inviter": names.get(i.pop("created_by"))} for i in items]
