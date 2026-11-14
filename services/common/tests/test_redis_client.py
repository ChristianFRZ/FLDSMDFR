from fakeredis import aioredis as fakeredis

from meloxo_common import redis_client
from meloxo_common.config import get_base_settings


def test_empty_url_disables_redis(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "")
    get_base_settings.cache_clear()
    redis_client.override_redis(None)
    assert redis_client.get_redis() is None
    get_base_settings.cache_clear()


def test_override_returns_given_client(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "")
    get_base_settings.cache_clear()
    fake = fakeredis.FakeRedis(decode_responses=True)
    redis_client.override_redis(fake)
    assert redis_client.get_redis() is fake
    redis_client.override_redis(None)
    assert redis_client.get_redis() is None
    get_base_settings.cache_clear()
