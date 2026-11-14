"""Cliente de Redis compartido. Sin `REDIS_URL` no hay Redis: quien lo usa debe tolerar `None`."""
from redis.asyncio import Redis

from meloxo_common.config import get_base_settings

_client: Redis | None = None
_override: Redis | None = None


def get_redis() -> Redis | None:
    if _override is not None:
        return _override
    global _client
    url = get_base_settings().REDIS_URL
    if not url:
        return None
    if _client is None:
        _client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=5)
    return _client


def override_redis(client: Redis | None) -> None:
    """Para pruebas: fija el cliente que devuelve `get_redis()`. `None` vuelve al de la URL."""
    global _override
    _override = client
