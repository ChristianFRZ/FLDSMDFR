"""Reproducciones simuladas de la semilla de demo."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, insert

from app.core.db import session_scope
from app.modules.playback.models import Playback, PlaybackCounter

CHUNK = 5000
DEMO_DUPLICATES = "duplicates_demo"


@dataclass(frozen=True)
class DemoPlay:
    user_id: UUID
    song_id: UUID
    listened_seconds: int
    started_at: datetime


async def insert_demo_playbacks(plays: list[DemoPlay], duplicates: int) -> None:
    rows = [
        {
            "playback_id": uuid4(),
            "user_id": play.user_id,
            "song_id": play.song_id,
            "listened_seconds": play.listened_seconds,
            "started_at": play.started_at,
            "is_demo": True,
        }
        for play in plays
    ]
    async with session_scope() as session:
        for start in range(0, len(rows), CHUNK):
            await session.execute(insert(Playback), rows[start : start + CHUNK])
        session.add(PlaybackCounter(key=DEMO_DUPLICATES, value=duplicates))


async def clear_demo_playbacks() -> None:
    async with session_scope() as session:
        await session.execute(delete(Playback).where(Playback.is_demo.is_(True)))
        await session.execute(delete(PlaybackCounter).where(PlaybackCounter.key == DEMO_DUPLICATES))
