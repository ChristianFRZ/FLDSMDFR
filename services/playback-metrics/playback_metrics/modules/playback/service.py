from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from meloxo_common.auth import CurrentUser
from meloxo_common.playback_queue import QueuedEvent
from meloxo_common.pagination import PageParams, page_body

from playback_metrics.clients.catalog import get_songs
from playback_metrics.modules.playback.models import Playback, PlaybackCounter

DUPLICATES = "duplicates_discarded"
EVENTS_DISCARDED = "events_discarded"


async def history(session: AsyncSession, user: CurrentUser, params: PageParams) -> dict:
    mine = Playback.user_id == user.id
    total = await session.scalar(select(func.count()).select_from(Playback).where(mine))
    query = (
        select(Playback)
        .where(mine)
        .order_by(Playback.seq.desc())
        .limit(params.size)
        .offset((params.page - 1) * params.size)
    )
    rows = list((await session.execute(query)).scalars())
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    songs = await get_songs(list({r.song_id for r in rows}))
    items = [
        {
            "playback_id": r.playback_id,
            "listened_seconds": r.listened_seconds,
            "started_at": r.started_at,
            "song": songs.get(r.song_id),
        }
        for r in rows
    ]
    return page_body(items, total, params)


async def _bump(session: AsyncSession, key: str) -> None:
    counter = insert(PlaybackCounter).values(key=key, value=1)
    await session.execute(
        counter.on_conflict_do_update(index_elements=[PlaybackCounter.key], set_={"value": PlaybackCounter.value + 1})
    )


async def count_discarded(session: AsyncSession) -> None:
    """Un mensaje de la cola que no se pudo aplicar ni se podrá nunca."""
    await _bump(session, EVENTS_DISCARDED)
    await session.commit()


async def apply_event(session: AsyncSession, event: QueuedEvent) -> Literal["created", "duplicate", "progress", "discarded"]:
    """Aplica un evento de la cola. Catálogo ya validó la pista; aquí solo se guarda."""
    if event.type == "record":
        statement = (
            insert(Playback)
            .values(
                playback_id=event.playback_id,
                user_id=event.user_id,
                song_id=event.song_id,
                listened_seconds=event.listened_seconds,
                started_at=datetime.fromisoformat(event.received_at),  # cuándo se escuchó, no cuándo se aplicó
            )
            .on_conflict_do_nothing(index_elements=[Playback.playback_id])
            .returning(Playback.seq)
        )
        created = (await session.execute(statement)).first() is not None
        if not created:
            await _bump(session, DUPLICATES)
        await session.commit()
        return "created" if created else "duplicate"
    owner = await session.scalar(select(Playback.user_id).where(Playback.playback_id == event.playback_id))
    if owner is None or owner != event.user_id:
        await _bump(session, EVENTS_DISCARDED)
        await session.commit()
        return "discarded"
    await session.execute(
        update(Playback)
        .where(Playback.playback_id == event.playback_id)
        .values(listened_seconds=func.greatest(Playback.listened_seconds, event.listened_seconds))
    )
    await session.commit()
    return "progress"
