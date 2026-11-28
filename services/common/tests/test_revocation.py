import asyncio
import time
from uuid import uuid4

import pytest
from fakeredis import aioredis as fakeredis

from meloxo_common import revocation
from meloxo_common.redis_client import override_redis


@pytest.fixture(autouse=True)
def fake():
    client = fakeredis.FakeRedis(decode_responses=True)
    override_redis(client)
    revocation._skip_until = 0.0
    yield client
    override_redis(None)
    revocation._skip_until = 0.0


class Broken:
    """Cliente que falla o tarda: lo que Redis haría caído o saturado."""

    def __init__(self, delay: float = 0, error: Exception | None = None):
        self.delay, self.error, self.calls = delay, error, 0

    async def set(self, *args, **kwargs):
        return await self._act()

    async def get(self, *args, **kwargs):
        return await self._act()

    async def _act(self):
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return None


async def test_revoke_then_read_returns_timestamp():
    user = uuid4()
    before = time.time()
    await revocation.revoke(user)
    after = await revocation.revoked_after(user)
    assert after is not None and before <= after <= time.time()


async def test_read_returns_none_without_key():
    assert await revocation.revoked_after(uuid4()) is None


async def test_key_has_ttl_of_960_seconds(fake):
    user = uuid4()
    await revocation.revoke(user)
    assert 950 < await fake.ttl(f"revoked_after:{user}") <= 960


async def test_revoke_swallows_redis_errors():
    override_redis(Broken(error=ConnectionError("caído")))
    await revocation.revoke(uuid4())


async def test_read_returns_none_when_redis_fails():
    override_redis(Broken(error=ConnectionError("caído")))
    assert await revocation.revoked_after(uuid4()) is None


async def test_read_skips_redis_for_5s_after_failure():
    broken = Broken(error=ConnectionError("caído"))
    override_redis(broken)
    await revocation.revoked_after(uuid4())
    await revocation.revoked_after(uuid4())
    assert broken.calls == 1


async def test_read_gives_up_after_300ms():
    override_redis(Broken(delay=2))
    start = time.monotonic()
    assert await revocation.revoked_after(uuid4()) is None
    assert time.monotonic() - start < 0.6
