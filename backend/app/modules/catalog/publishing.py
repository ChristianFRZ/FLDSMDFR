"""Publicación programada y moderación."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.core.errors import AppError
from app.core.pagination import PageParams
from app.modules.catalog.models import Artist, PublishedEvent, Song
from app.modules.catalog.schemas import SongSummary
from app.modules.catalog.service import to_summary
from app.modules.users.public import record_audit


async def record_published(session: AsyncSession, song_id: UUID) -> None:
    """Registro único de track_published: una pista solo se anuncia una vez."""
    await session.execute(insert(PublishedEvent).values(song_id=song_id).on_conflict_do_nothing())


async def publish_due_tracks() -> int:
    """SKIP LOCKED reparte las pistas entre procesos: ninguna se publica dos veces."""
    now = datetime.now(UTC)
    query = (
        select(Song.id)
        .where(Song.status == "scheduled", Song.publish_at <= now)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )
    async with session_scope() as session:
        ids = list((await session.execute(query)).scalars())
        for song_id in ids:
            song = await session.get(Song, song_id)
            song.status = "published"
            song.published_at = now
            await record_published(session, song_id)
    return len(ids)


async def _load(session: AsyncSession, song_id: UUID) -> Song:
    song = await session.get(Song, song_id)
    if song is None:
        raise AppError(404, "song_not_found", "Canción no encontrada")
    return song


async def hide_song(session: AsyncSession, actor_id: UUID, song_id: UUID, reason: str) -> SongSummary:
    song = await _load(session, song_id)
    if not song.hidden_by_admin:
        song.status_before_hide = song.status
    song.status = "hidden"
    song.hidden_reason = reason
    song.hidden_by_admin = True
    await session.commit()
    await record_audit(actor_id, "hide_song", "song", str(song_id), {"reason": reason})
    return to_summary(song)


async def restore_song(session: AsyncSession, actor_id: UUID, song_id: UUID) -> SongSummary:
    """Devuelve la pista a como estaba: restaurar nunca publica algo que no estuviera publicado."""
    song = await _load(session, song_id)
    if not song.hidden_by_admin:
        raise AppError(409, "not_hidden_by_admin", "Esta pista la ocultó su Compositor, no un administrador")
    song.status = song.status_before_hide or ("published" if song.published_at else "draft")
    song.status_before_hide = None
    song.hidden_reason = None
    song.hidden_by_admin = False
    await session.commit()
    await record_audit(actor_id, "restore_song", "song", str(song_id))
    return to_summary(song)


async def list_all_songs(
    session: AsyncSession, params: PageParams, q: str | None, status: str | None, source: str | None
) -> tuple[list[dict], int]:
    filters = []
    if q:
        filters.append(Song.title.ilike(f"%{q}%") | Artist.name.ilike(f"%{q}%"))
    if status:
        filters.append(Song.status == status)
    if source:
        filters.append(Song.source == source)
    total = await session.scalar(select(func.count(Song.id)).join(Artist, Song.artist_id == Artist.id).where(*filters))
    query = (
        select(Song)
        .join(Artist, Song.artist_id == Artist.id)
        .where(*filters)
        .order_by(Song.created_at.desc(), Song.id)
        .offset(params.offset)
        .limit(params.size)
    )
    songs = (await session.execute(query)).unique().scalars()
    return [{**to_summary(s).__dict__, "hidden_by_admin": s.hidden_by_admin} for s in songs], total or 0
