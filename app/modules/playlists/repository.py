import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playlists.models import (
    Playlist,
    PlaylistInvite,
    PlaylistInviteClaim,
    PlaylistMember,
    PlaylistSong,
)


async def get_owned(
    session: AsyncSession,
    owner_id: uuid.UUID,
    playlist_id: uuid.UUID,
    for_update: bool = False,
):
    """`for_update` bloquea la fila del casete: serializa las mutaciones concurrentes."""
    stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == owner_id)
    if for_update:
        stmt = stmt.with_for_update()
    return await session.scalar(stmt)


def _can_read(user_id: uuid.UUID):
    member = exists().where(
        PlaylistMember.playlist_id == Playlist.id, PlaylistMember.user_id == user_id
    )
    return or_(Playlist.owner_id == user_id, member)


async def get_readable(
    session: AsyncSession,
    user_id: uuid.UUID,
    playlist_id: uuid.UUID,
    for_update: bool = False,
) -> Playlist | None:
    """Casete del que la persona es dueña o miembro."""
    stmt = select(Playlist).where(Playlist.id == playlist_id, _can_read(user_id))
    if for_update:
        stmt = stmt.with_for_update(of=Playlist)
    return await session.scalar(stmt)


async def list_members(session: AsyncSession, playlist_id: uuid.UUID) -> list[PlaylistMember]:
    stmt = (
        select(PlaylistMember)
        .where(PlaylistMember.playlist_id == playlist_id)
        .order_by(PlaylistMember.joined_at, PlaylistMember.user_id)
    )
    return list((await session.scalars(stmt)).all())


async def get_member(
    session: AsyncSession, playlist_id: uuid.UUID, user_id: uuid.UUID
) -> PlaylistMember | None:
    return await session.get(PlaylistMember, (playlist_id, user_id))


async def add(session: AsyncSession, playlist: Playlist) -> Playlist:
    session.add(playlist)
    await session.commit()
    return playlist


async def list_with_counts(session: AsyncSession, user_id: uuid.UUID) -> list[tuple[Playlist, int]]:
    """Casetes propios y colaborativos, el modificado más recientemente primero."""
    count = func.count(PlaylistSong.song_id)
    stmt = (
        select(Playlist, count)
        .outerjoin(PlaylistSong, PlaylistSong.playlist_id == Playlist.id)
        .where(_can_read(user_id))
        .group_by(Playlist.id)
        .order_by(Playlist.updated_at.desc(), Playlist.id)
    )
    return [(p, n) for p, n in (await session.execute(stmt)).all()]


async def count_songs(session: AsyncSession, playlist_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(PlaylistSong)
        .where(PlaylistSong.playlist_id == playlist_id)
    )
    return await session.scalar(stmt) or 0


async def list_songs(session: AsyncSession, playlist_id: uuid.UUID) -> list[PlaylistSong]:
    stmt = (
        select(PlaylistSong)
        .where(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position)
    )
    return list((await session.scalars(stmt)).all())


async def max_position(session: AsyncSession, playlist_id: uuid.UUID) -> int:
    stmt = select(func.max(PlaylistSong.position)).where(PlaylistSong.playlist_id == playlist_id)
    return await session.scalar(stmt) or 0


async def get_entry(
    session: AsyncSession, playlist_id: uuid.UUID, song_id: uuid.UUID
) -> PlaylistSong | None:
    return await session.get(PlaylistSong, (playlist_id, song_id))


async def delete_playlist(session: AsyncSession, playlist: Playlist) -> None:
    await session.delete(playlist)
    await session.commit()


async def delete_entry(session: AsyncSession, entry: PlaylistSong) -> None:
    await session.execute(
        delete(PlaylistSong).where(
            PlaylistSong.playlist_id == entry.playlist_id, PlaylistSong.song_id == entry.song_id
        )
    )


def touch(playlist: Playlist) -> None:
    playlist.updated_at = datetime.now(UTC)


async def revoke_invites(session: AsyncSession, playlist_id: uuid.UUID) -> None:
    await session.execute(
        update(PlaylistInvite)
        .where(PlaylistInvite.playlist_id == playlist_id, PlaylistInvite.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def get_active_invite(session: AsyncSession, token: str) -> PlaylistInvite | None:
    stmt = select(PlaylistInvite).where(
        PlaylistInvite.token == token, PlaylistInvite.revoked_at.is_(None)
    )
    return await session.scalar(stmt)


async def get_claim(
    session: AsyncSession, token: str, user_id: uuid.UUID
) -> PlaylistInviteClaim | None:
    return await session.get(PlaylistInviteClaim, (token, user_id))


async def pending_claims(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[PlaylistInviteClaim, PlaylistInvite, Playlist]]:
    stmt = (
        select(PlaylistInviteClaim, PlaylistInvite, Playlist)
        .join(PlaylistInvite, PlaylistInvite.token == PlaylistInviteClaim.token)
        .join(Playlist, Playlist.id == PlaylistInvite.playlist_id)
        .where(
            PlaylistInviteClaim.user_id == user_id,
            PlaylistInviteClaim.status == "pending",
            PlaylistInvite.revoked_at.is_(None),
        )
        .order_by(PlaylistInviteClaim.claimed_at.desc())
    )
    return [tuple(row) for row in (await session.execute(stmt)).all()]
