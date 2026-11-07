"""Tablas de resumen. Lee los eventos por la interfaz pública de playback, nunca sus tablas."""
import asyncio
from collections import Counter
from datetime import UTC, datetime, timedelta
from itertools import takewhile

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.db import session_scope
from app.modules.analytics.models import AggCursor, PlaysHourly, UserPlays
from app.modules.catalog.public import get_songs
from app.modules.playback.public import PlaybackEvent, events_since

BATCH = 2000
LOCK_KEY = 7_301_501
NO_GENRE = "sin género"


async def _upsert(session, model, keys: Counter, columns: tuple[str, ...], artists: dict) -> None:
    rows = [{**dict(zip(columns, key)), **artists[key], "plays": plays} for key, plays in keys.items()]
    if not rows:
        return
    statement = insert(model).values(rows)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=list(columns),
            set_={"plays": model.plays + statement.excluded.plays},
        )
    )


async def refresh_aggregates(settle_seconds: float = 1.0) -> int:
    """Procesa un lote y devuelve cuántos eventos sumó.

    `seq` se asigna al insertar, no al confirmar: un evento puede aparecer después de otro con `seq` mayor. Por eso el
    lote se corta en el primer evento demasiado reciente, para que el cursor no pase por encima de él.
    """
    async with session_scope() as session:
        if not await session.scalar(select(func.pg_try_advisory_xact_lock(LOCK_KEY))):
            return 0
        cursor = await session.get(AggCursor, 1)
        if cursor is None:
            cursor = AggCursor(id=1, last_seq=0)
            session.add(cursor)
        cutoff = datetime.now(UTC) - timedelta(seconds=settle_seconds)
        events = await events_since(cursor.last_seq, BATCH)
        settled: list[PlaybackEvent] = list(takewhile(lambda e: e.started_at <= cutoff, events))
        if not settled:
            return 0
        songs = await get_songs(list({e.song_id for e in settled}))
        hourly, personal, extra_hourly, extra_personal = Counter(), Counter(), {}, {}
        for event in settled:
            song = songs.get(event.song_id)
            if song is None:
                continue
            # Una sola fila por reproducción: el género principal, para no contarla dos veces en el top.
            genre = song.genres[0] if song.genres else NO_GENRE
            hour = event.started_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            hour_key = (hour, event.song_id)
            hourly[hour_key] += 1
            extra_hourly[hour_key] = {"artist_id": song.artist_id, "genre": genre}
            user_key = (event.user_id, event.song_id)
            personal[user_key] += 1
            extra_personal[user_key] = {"artist_id": song.artist_id, "genre": genre}
        await _upsert(session, PlaysHourly, hourly, ("hour", "song_id"), extra_hourly)
        await _upsert(session, UserPlays, personal, ("user_id", "song_id"), extra_personal)
        cursor.last_seq = settled[-1].seq
        return len(settled)


async def catch_up_aggregates() -> None:
    """Procesa hasta quedar al día, sin ventana de asentamiento. El proceso de la app puede tener el candado un momento."""
    while await lag_seconds() is not None:
        if not await refresh_aggregates(settle_seconds=0):
            await asyncio.sleep(0.2)


async def rebuild_aggregates() -> None:
    """Rehace los agregados desde los eventos. Solo hace falta cuando se borran eventos, como al limpiar la demo."""
    async with session_scope() as session:
        await session.execute(select(func.pg_advisory_xact_lock(LOCK_KEY)))
        await session.execute(delete(PlaysHourly))
        await session.execute(delete(UserPlays))
        await session.execute(delete(AggCursor))
    await catch_up_aggregates()


async def lag_seconds() -> float | None:
    """Antigüedad del evento más viejo sin agregar, o None si está al día."""
    async with session_scope() as session:
        cursor = await session.get(AggCursor, 1)
    pending = await events_since(cursor.last_seq if cursor else 0, 1)
    if not pending:
        return None
    return (datetime.now(UTC) - pending[0].started_at).total_seconds()
