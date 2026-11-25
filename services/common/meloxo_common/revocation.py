"""Lista de revocación de sesiones en Redis. Falla abierto: sin Redis manda la caché de estado de 30 s."""
import asyncio
import logging
import time
from uuid import UUID

from meloxo_common import redis_client

log = logging.getLogger(__name__)

REVOKED_TTL_SECONDS = 960  # vida del token (15 min) más un margen
READ_TIMEOUT_SECONDS = 0.3
SKIP_AFTER_FAILURE_SECONDS = 5.0
_skip_until = 0.0


def _key(user_id: UUID | str) -> str:
    return f"revoked_after:{user_id}"


async def revoke(user_id: UUID) -> None:
    """Invalida los tokens emitidos hasta ahora. Nunca lanza: una caída de Redis no frena la acción del admin."""
    redis = redis_client.get_redis()
    if redis is None:
        return
    try:
        await asyncio.wait_for(redis.set(_key(user_id), time.time(), ex=REVOKED_TTL_SECONDS), READ_TIMEOUT_SECONDS * 3)
    except Exception as exc:
        log.warning("No se pudo registrar la revocación de %s: %s", user_id, type(exc).__name__)


async def revoked_after(user_id: UUID | str) -> float | None:
    """Hora de la última revocación, o `None` si no hay o no se pudo consultar."""
    global _skip_until
    redis = redis_client.get_redis()
    if redis is None or time.monotonic() < _skip_until:
        return None
    try:
        value = await asyncio.wait_for(redis.get(_key(user_id)), READ_TIMEOUT_SECONDS)
    except Exception as exc:
        _skip_until = time.monotonic() + SKIP_AFTER_FAILURE_SECONDS
        log.warning("No se pudo consultar la revocación: %s", type(exc).__name__)
        return None
    return float(value) if value is not None else None
