"""Consumidor de la cola de reproducciones: aplica en orden y acusa (`XACK`) solo después del commit."""
import asyncio
import logging

from redis.asyncio import Redis

from meloxo_common import playback_queue as queue
from meloxo_common import redis_client
from meloxo_common.db import session_scope
from playback_metrics.modules.playback import service

log = logging.getLogger(__name__)

CONSUMER = "playback-metrics"


async def _handle(redis: Redis, entry_id: str, fields: dict[str, str] | None) -> bool:
    """True si el mensaje quedó resuelto y acusado; False si falló por algo transitorio y sigue pendiente."""
    try:
        try:
            event = queue.from_fields(fields or {})
        except ValueError as exc:
            log.warning("Mensaje %s inválido, se descarta: %s", entry_id, exc)
            async with session_scope() as session:
                await service.count_discarded(session)
        else:
            async with session_scope() as session:
                result = await service.apply_event(session, event)
            if result == "discarded":
                log.warning("Evento %s descartado: la reproducción no existe o es de otra persona", entry_id)
        await redis.xack(queue.STREAM, queue.GROUP, entry_id)
        return True
    except Exception:
        log.exception("No se pudo aplicar el mensaje %s; se reintentará", entry_id)
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

    Si un mensaje falla se detiene sin leer lo siguiente, para no aplicar un `progress` antes que su `record`.
    Devuelve cuántos mensajes quedaron resueltos.
    """
    await queue.ensure_group(redis)
    done = 0

    async def drain(entries: list) -> bool:
        nonlocal done
        for entry_id, fields in entries:
            if not await _handle(redis, entry_id, fields):
                await asyncio.sleep(retry_delay)
                return False
            done += 1
        return True

    own = await redis.xreadgroup(queue.GROUP, consumer, {queue.STREAM: "0"}, count=count)
    entries = own[0][1] if own else []
    if entries:
        await drain(entries)
        return done
    claimed = await redis.xautoclaim(queue.STREAM, queue.GROUP, consumer, min_idle_time=min_idle_ms, start_id="0-0", count=count)
    entries = claimed[1] if claimed else []
    if entries:
        await drain(entries)
        return done
    new = await redis.xreadgroup(queue.GROUP, consumer, {queue.STREAM: ">"}, count=count, block=block_ms)
    await drain(new[0][1] if new else [])
    return done


async def run_consumer(consumer: str = CONSUMER) -> None:
    while True:
        redis = redis_client.get_redis()
        if redis is None:
            return
        try:
            await consume_once(redis, consumer)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Falló el consumidor de reproducciones; se reintenta en 1 s")
            await asyncio.sleep(1)
