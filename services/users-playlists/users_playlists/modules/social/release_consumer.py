"""Consumidor de `track_published`: guarda cada lanzamiento y acusa (`XACK`) solo después del commit."""
import asyncio
import logging
from datetime import datetime

from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert

from meloxo_common import redis_client
from meloxo_common import track_events as events
from meloxo_common.db import session_scope
from users_playlists.modules.social.models import ReleaseEvent

log = logging.getLogger(__name__)

CONSUMER = "users-playlists"


async def _deliveries(redis: Redis, entry_id: str) -> int:
    rows = await redis.xpending_range(events.STREAM, events.GROUP, min=entry_id, max=entry_id, count=1)
    return rows[0]["times_delivered"] if rows else 1


async def _dead_letter(redis: Redis, entry_id: str, fields: dict[str, str], reason: str) -> None:
    await events.send_to_dlq(redis, entry_id, fields, reason)
    await redis.xack(events.STREAM, events.GROUP, entry_id)


async def _handle(redis: Redis, entry_id: str, fields: dict[str, str] | None) -> bool:
    """True si el mensaje quedó resuelto (guardado o en la DLQ) y acusado; False si falló y sigue pendiente."""
    fields = fields or {}
    try:
        # Cuenta la entrega actual: con más de MAX_ATTEMPTS ya se intentó MAX_ATTEMPTS veces.
        if await _deliveries(redis, entry_id) > events.MAX_ATTEMPTS:
            log.error("Mensaje %s agotó %d intentos; va a la cola de mensajes muertos", entry_id, events.MAX_ATTEMPTS)
            await _dead_letter(redis, entry_id, fields, f"agotó MAX_ATTEMPTS ({events.MAX_ATTEMPTS}) intentos")
            return True
        try:
            event = events.from_fields(fields)
        except ValueError as exc:
            log.warning("Mensaje %s inválido; va a la cola de mensajes muertos: %s", entry_id, exc)
            await _dead_letter(redis, entry_id, fields, str(exc))
            return True
        statement = insert(ReleaseEvent).values(
            song_id=event.song_id,
            artist_id=event.artist_id,
            published_at=datetime.fromisoformat(event.published_at),
            song=event.song,
        )
        async with session_scope() as session:
            await session.execute(statement.on_conflict_do_nothing(index_elements=[ReleaseEvent.song_id]))
        await redis.xack(events.STREAM, events.GROUP, entry_id)
        return True
    except Exception:
        log.exception("No se pudo guardar el mensaje %s; se reintentará", entry_id)
        return False


async def consume_once(
    redis: Redis,
    consumer: str = CONSUMER,
    block_ms: int = 1000,
    count: int = 50,
    min_idle_ms: int = 30_000,
    retry_delay: float = 1.0,
) -> int:
    """Una vuelta: primero lo pendiente propio, luego lo pendiente de otros consumidores y al final lo nuevo.

    Si un mensaje falla se detiene sin leer lo siguiente. Devuelve cuántos mensajes quedaron resueltos.
    """
    await events.ensure_group(redis)
    done = 0

    async def drain(entries: list) -> None:
        nonlocal done
        for entry_id, fields in entries:
            if not await _handle(redis, entry_id, fields):
                await asyncio.sleep(retry_delay)
                return
            done += 1

    own = await redis.xreadgroup(events.GROUP, consumer, {events.STREAM: "0"}, count=count)
    entries = own[0][1] if own else []
    if entries:
        await drain(entries)
        return done
    claimed = await redis.xautoclaim(events.STREAM, events.GROUP, consumer, min_idle_time=min_idle_ms, start_id="0-0", count=count)
    entries = claimed[1] if claimed else []
    if entries:
        await drain(entries)
        return done
    new = await redis.xreadgroup(events.GROUP, consumer, {events.STREAM: ">"}, count=count, block=block_ms)
    await drain(new[0][1] if new else [])
    return done


async def run_release_consumer(consumer: str = CONSUMER) -> None:
    while True:
        redis = redis_client.get_redis()
        if redis is None:
            return
        try:
            await consume_once(redis, consumer)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Falló el consumidor de lanzamientos; se reintenta en 1 s")
            await asyncio.sleep(1)
