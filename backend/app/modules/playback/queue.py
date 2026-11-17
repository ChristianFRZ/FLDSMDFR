"""Entrega diferida con Redis Streams. El acuse sigue al commit en PostgreSQL."""
import logging
import socket
from functools import lru_cache
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.db import session_scope
from app.core.errors import AppError
from app.modules.playback.schemas import PlaybackIn
from app.modules.playback.service import record

STREAM = "playbacks"
GROUP = "playback-metrics"
CONSUMER = socket.gethostname()
log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def connection():
    return Redis.from_url(get_settings().REDIS_URL, decode_responses=True,
                          socket_connect_timeout=1.5, socket_timeout=1.5, socket_keepalive=True)


async def enqueue(user, data, delivery_id):
    try:
        await connection().xadd(STREAM, {"delivery_id": str(delivery_id), "user_id": str(user.id), "data": data.model_dump_json()})
    except RedisError as exc:
        log.warning("Redis no pudo confirmar la entrega: %s", exc)
        raise AppError(503, "queue_unavailable", "Reintenta el envío de la reproducción") from exc


async def consume():
    if not get_settings().REDIS_URL:
        return
    redis = connection()
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
    _, pending, *_ = await redis.xautoclaim(STREAM, GROUP, CONSUMER, 15000, count=32)
    fresh = await redis.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=32)
    for message_id, fields in [*pending, *(fresh[0][1] if fresh else [])]:
        try:
            async with session_scope() as session:
                await record(session, CurrentUser(UUID(fields["user_id"]), "listener"),
                             PlaybackIn.model_validate_json(fields["data"]), delivery_id=UUID(fields["delivery_id"]))
        except AppError as exc:
            if exc.status >= 500:
                continue
            log.warning("Reproducción rechazada %s: %s", message_id, exc.code)
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.xack(STREAM, GROUP, message_id).xdel(STREAM, message_id).execute()


async def close_queue():
    if connection.cache_info().currsize:
        await connection().aclose()
        connection.cache_clear()
