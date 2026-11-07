"""Interfaz pública de modules.playback. Solo tipos simples; cada función abre su sesión."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.core.db import session_scope
from app.modules.playback.models import Playback, PlaybackCounter
from app.modules.playback.schemas import PlaybackEvent, RetentionStats
from app.modules.playback.service import DUPLICATES
from app.modules.playback.demo import DEMO_DUPLICATES, DemoPlay, clear_demo_playbacks, insert_demo_playbacks  # noqa: F401

__all__ = ["PlaybackEvent", "RetentionStats", "duplicates_discarded", "events_since", "recent_activity", "retention_for_songs", "DemoPlay", "clear_demo_playbacks", "insert_demo_playbacks"]


async def recent_activity(minutes: int) -> tuple[int, int]:
    """Personas y reproducciones reales en la ventana. Un evento llega al terminar de escuchar, no mientras suena."""
    since = datetime.now(UTC) - timedelta(minutes=minutes)
    query = select(func.count(func.distinct(Playback.user_id)), func.count()).where(
        Playback.started_at >= since, Playback.is_demo.is_(False)
    )
    async with session_scope() as session:
        listeners, plays = (await session.execute(query)).one()
    return listeners, plays


async def events_since(cursor: int, limit: int) -> list[PlaybackEvent]:
    query = select(Playback).where(Playback.seq > cursor).order_by(Playback.seq).limit(limit)
    async with session_scope() as session:
        return [
            PlaybackEvent(
                seq=r.seq,
                playback_id=r.playback_id,
                user_id=r.user_id,
                song_id=r.song_id,
                listened_seconds=r.listened_seconds,
                started_at=r.started_at,
                is_demo=r.is_demo,
            )
            for r in (await session.execute(query)).scalars()
        ]


async def duplicates_discarded() -> int:
    async with session_scope() as session:
        total = select(func.sum(PlaybackCounter.value)).where(PlaybackCounter.key.in_([DUPLICATES, DEMO_DUPLICATES]))
        return await session.scalar(total) or 0


async def retention_for_songs(song_ids: list[UUID], durations: dict[UUID, float]) -> RetentionStats:
    """Cuántas reproducciones llegan a 10 s, a la mitad y al final. Una pista sin duración solo cuenta en 10 s."""
    if not song_ids:
        return RetentionStats(0, 0, 0)
    query = (
        select(Playback.song_id, Playback.listened_seconds, func.count())
        .where(Playback.song_id.in_(song_ids))
        .group_by(Playback.song_id, Playback.listened_seconds)
    )
    at_10s = at_50 = at_100 = 0
    async with session_scope() as session:
        rows = (await session.execute(query)).all()
    for song_id, listened, plays in rows:
        duration = durations.get(song_id) or 0
        at_10s += plays if listened >= 10 else 0
        if duration > 0:
            at_50 += plays if listened * 2 >= duration else 0
            # El progreso va en segundos enteros: 40 s ya es el final de una pista de 40.05 s.
            at_100 += plays if listened >= int(duration) else 0
    return RetentionStats(at_10s, at_50, at_100)
