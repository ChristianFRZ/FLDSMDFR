import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playback.models import PlaybackEvent, SongPlayCount


async def record_event(
    session: AsyncSession,
    playback_id: uuid.UUID,
    song_id: uuid.UUID,
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
            song_id=song_id,
            user_id=user_id,
            listened_seconds=listened_seconds,
            occurred_at=occurred_at,
        )
        .on_conflict_do_nothing(index_elements=[PlaybackEvent.playback_id])
        .returning(PlaybackEvent.playback_id)
    )
    if inserted is None:
        await session.rollback()
        return False
    upsert = insert(SongPlayCount).values(song_id=song_id, play_count=1, last_played_at=func.now())
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
) -> tuple[list[tuple[uuid.UUID, datetime]], int]:
    """Una fila por canción con su escucha más reciente, la más reciente primero."""
    last = func.max(PlaybackEvent.occurred_at).label("last")
    stmt = (
        select(PlaybackEvent.song_id, last)
        .where(PlaybackEvent.user_id == user_id)
        .group_by(PlaybackEvent.song_id)
        .order_by(last.desc(), PlaybackEvent.song_id)
        .limit(limit)
        .offset(offset)
    )
    total = await session.scalar(
        select(func.count(func.distinct(PlaybackEvent.song_id))).where(
            PlaybackEvent.user_id == user_id
        )
    )
    return [(sid, at) for sid, at in (await session.execute(stmt)).all()], total or 0
