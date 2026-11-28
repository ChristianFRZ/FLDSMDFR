import asyncio

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select

from meloxo_common import track_events
from meloxo_common.db import session_scope
from meloxo_common.redis_client import override_redis
from catalog_streaming.modules.catalog.models import PublishedEvent
from catalog_streaming.modules.catalog.outbox import relay_published_events


async def add_event(song):
    async with session_scope() as session:
        session.add(PublishedEvent(song_id=song.id))


async def relayed_at(song):
    async with session_scope() as session:
        return await session.scalar(select(PublishedEvent.relayed_at).where(PublishedEvent.song_id == song.id))


async def test_relays_published_song_and_marks_it(make_song, fake_redis):
    song = await make_song(title="Nueva")
    await add_event(song)
    assert await relay_published_events() == 1
    [(_, fields)] = await fake_redis.xrange(track_events.STREAM)
    event = track_events.from_fields(fields)
    assert event.song_id == song.id
    assert event.artist_id == song.artist_id
    assert event.song["title"] == "Nueva"
    assert await relayed_at(song) is not None


async def test_second_run_publishes_nothing(make_song, fake_redis):
    await add_event(await make_song())
    assert await relay_published_events() == 1
    assert await relay_published_events() == 0
    assert await fake_redis.xlen(track_events.STREAM) == 1


async def test_jamendo_song_is_marked_but_not_published(make_song, fake_redis):
    song = await make_song(source="jamendo", artist="De Jamendo")
    await add_event(song)
    assert await relay_published_events() == 0
    assert await fake_redis.xlen(track_events.STREAM) == 0
    assert await relayed_at(song) is not None


async def test_hidden_song_is_marked_but_not_published(make_song, fake_redis):
    song = await make_song(status="hidden")
    await add_event(song)
    assert await relay_published_events() == 0
    assert await fake_redis.xlen(track_events.STREAM) == 0
    assert await relayed_at(song) is not None


async def test_redis_failure_leaves_relayed_at_null(make_song, fake_redis):
    song = await make_song()
    await add_event(song)

    class BrokenRedis:
        async def xadd(self, *args, **kwargs):
            raise RedisConnectionError("caído")

    override_redis(BrokenRedis())
    with pytest.raises(RedisConnectionError):
        await relay_published_events()
    assert await relayed_at(song) is None

    override_redis(fake_redis)
    assert await relay_published_events() == 1
    assert await relayed_at(song) is not None


async def test_no_redis_url_raises_and_leaves_relayed_at_null(make_song):
    song = await make_song()
    await add_event(song)
    override_redis(None)
    with pytest.raises(RuntimeError):
        await relay_published_events()
    assert await relayed_at(song) is None


async def test_two_concurrent_relays_publish_each_event_once(make_song, fake_redis):
    for i in range(3):
        await add_event(await make_song(title=f"P{i}"))
    counts = await asyncio.gather(relay_published_events(), relay_published_events())
    assert sum(counts) == 3
    assert await fake_redis.xlen(track_events.STREAM) == 3
