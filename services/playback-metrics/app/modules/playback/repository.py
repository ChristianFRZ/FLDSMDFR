import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.catalog_schemas import SongOut
from app.modules.playback.models import PlaybackEvent, SongPlayCount


@dataclass(frozen=True)
class HistoryRow:
    """Una canción del historial con su escucha más reciente y la copia de ese evento."""

    song_id: uuid.UUID
    last_played_at: datetime
    title: str | None
    artist: str | None
    album: str | None
    duration: int | None


def _snapshot(song: SongOut) -> dict:
    return {
        "title_snapshot": song.title,
        "artist_snapshot": song.artist,
        "album_snapshot": song.album,
        "duration_snapshot": song.duration_seconds,
    }


async def record_event(
    session: AsyncSession,
    playback_id: uuid.UUID,
    song: SongOut,
    user_id: uuid.UUID,
    listened_seconds: int,
    occurred_at: datetime,
) -> bool:
    """Registra el evento y suma al contador en una sola transaccion.

    El INSERT ... ON CONFLICT DO NOTHING es atomico: solo una peticion concurrente con el
    mismo `playback_id` recibe fila y, por tanto, solo esa incrementa el contador.
    """
    inserted = await session.scalar(
        insert(PlaybackEvent)
        .values(
            playback_id=playback_id,
            song_id=song.id,
            user_id=user_id,
            listened_seconds=listened_seconds,
            occurred_at=occurred_at,
            **_snapshot(song),
        )
        .on_conflict_do_nothing(index_elements=[PlaybackEvent.playback_id])
        .returning(PlaybackEvent.playback_id)
    )
    if inserted is None:
        await session.rollback()
        return False
    upsert = insert(SongPlayCount).values(song_id=song.id, play_count=1, last_played_at=func.now())
    await session.execute(
        upsert.on_conflict_do_update(
            index_elements=[SongPlayCount.song_id],
            set_={
                "play_count": SongPlayCount.play_count + 1,
                "last_played_at": func.now(),
            },
        )
    )
    await session.commit()
    return True


async def top_counts(
    session: AsyncSession, limit: int, offset: int = 0
) -> list[tuple[uuid.UUID, int]]:
    stmt = (
        select(SongPlayCount.song_id, SongPlayCount.play_count)
        .order_by(
            SongPlayCount.play_count.desc(),
            SongPlayCount.last_played_at.desc(),
            SongPlayCount.song_id,
        )
        .limit(limit)
        .offset(offset)
    )
    return [(song_id, count) for song_id, count in (await session.execute(stmt)).all()]


async def count_events(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(PlaybackEvent)) or 0


async def user_history(
    session: AsyncSession, user_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[HistoryRow], int]:
    """Una fila por canción con su escucha más reciente (y la copia de ese evento), la más
    reciente primero."""
    latest = (
        select(
            PlaybackEvent.song_id,
            PlaybackEvent.occurred_at,
            PlaybackEvent.title_snapshot,
            PlaybackEvent.artist_snapshot,
            PlaybackEvent.album_snapshot,
            PlaybackEvent.duration_snapshot,
        )
        .where(PlaybackEvent.user_id == user_id)
        .ext(distinct_on(PlaybackEvent.song_id))
        .order_by(PlaybackEvent.song_id, PlaybackEvent.occurred_at.desc())
        .subquery()
    )
    stmt = (
        select(latest)
        .order_by(latest.c.occurred_at.desc(), latest.c.song_id)
        .limit(limit)
        .offset(offset)
    )
    total = await session.scalar(
        select(func.count(func.distinct(PlaybackEvent.song_id))).where(
            PlaybackEvent.user_id == user_id
        )
    )
    rows = [HistoryRow(*row) for row in (await session.execute(stmt)).all()]
    return rows, total or 0


async def save_snapshots(session: AsyncSession, user_id: uuid.UUID, songs: list[SongOut]) -> None:
    """Actualiza la copia de los eventos de `user_id` con los datos vivos del catálogo."""
    for song in songs:
        await session.execute(
            update(PlaybackEvent)
            .where(PlaybackEvent.user_id == user_id, PlaybackEvent.song_id == song.id)
            .values(**_snapshot(song))
        )
    await session.commit()
