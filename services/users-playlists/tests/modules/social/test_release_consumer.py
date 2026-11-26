from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from meloxo_common import track_events as te
from meloxo_common.db import session_scope
from users_playlists.modules.social import release_consumer
from users_playlists.modules.social.models import ReleaseEvent


def event(**kw) -> te.TrackPublished:
    song_id, artist_id = uuid4(), uuid4()
    data = dict(
        song_id=song_id,
        artist_id=artist_id,
        published_at=datetime.now(UTC).isoformat(),
        song={"id": str(song_id), "title": "Pista", "artist_id": str(artist_id)},
    )
    data.update(kw)
    return te.TrackPublished(**data)


async def count_rows() -> int:
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(ReleaseEvent))


async def pending(redis) -> int:
    await te.ensure_group(redis)
    return (await redis.xpending(te.STREAM, te.GROUP))["pending"]


async def test_valid_event_is_stored_then_acked(fake_redis):
    sent = event()
    await te.enqueue(fake_redis, sent)
    assert await release_consumer.consume_once(fake_redis, block_ms=10) == 1
    async with session_scope() as session:
        row = await session.get(ReleaseEvent, sent.song_id)
    assert row.artist_id == sent.artist_id
    assert row.song["title"] == "Pista"
    assert await pending(fake_redis) == 0


async def test_duplicate_event_stores_one_row(fake_redis):
    sent = event()
    await te.enqueue(fake_redis, sent)
    await te.enqueue(fake_redis, sent)
    assert await release_consumer.consume_once(fake_redis, block_ms=10) == 2
    assert await count_rows() == 1
    assert await pending(fake_redis) == 0


async def test_invalid_message_goes_to_dlq_with_reason_and_is_acked(fake_redis):
    good = event()
    broken = te.to_fields(event())
    mismatch = te.to_fields(event())
    mismatch["song_id"] = str(uuid4())
    bad_uuid = te.to_fields(event())
    bad_uuid["artist_id"] = "roto"
    missing = te.to_fields(event())
    del missing["song"]
    for fields in (broken | {"song": "no es json"}, mismatch, bad_uuid, missing):
        await fake_redis.xadd(te.STREAM, fields)
    await te.enqueue(fake_redis, good)
    assert await release_consumer.consume_once(fake_redis, block_ms=10) == 5
    dead = await fake_redis.xrange(te.DLQ_STREAM)
    assert len(dead) == 4
    assert all(fields["reason"] and fields["original_id"] for _, fields in dead)
    assert await count_rows() == 1  # el válido que venía después no quedó atascado
    assert await pending(fake_redis) == 0


async def test_unacked_message_is_reclaimed_after_idle(fake_redis):
    sent = event()
    await te.enqueue(fake_redis, sent)
    await te.ensure_group(fake_redis)
    await fake_redis.xreadgroup(te.GROUP, "otro-consumidor", {te.STREAM: ">"}, count=10)
    assert await release_consumer.consume_once(fake_redis, "yo", block_ms=10, min_idle_ms=0) == 1
    assert await count_rows() == 1
    assert await pending(fake_redis) == 0


async def test_db_failure_keeps_message_pending(fake_redis, monkeypatch):
    await te.enqueue(fake_redis, event())

    def broken_session():
        raise ConnectionError("base caída")

    monkeypatch.setattr(release_consumer, "session_scope", broken_session)
    assert await release_consumer.consume_once(fake_redis, block_ms=10, retry_delay=0) == 0
    assert await pending(fake_redis) == 1
    assert await fake_redis.xlen(te.DLQ_STREAM) == 0


async def test_message_over_max_attempts_goes_to_dlq(fake_redis, monkeypatch):
    await te.enqueue(fake_redis, event())

    def broken_session():
        raise ConnectionError("base caída")

    monkeypatch.setattr(release_consumer, "session_scope", broken_session)
    for _ in range(te.MAX_ATTEMPTS + 1):
        await release_consumer.consume_once(fake_redis, block_ms=10, retry_delay=0)
    [(_, dead)] = await fake_redis.xrange(te.DLQ_STREAM)
    assert "MAX_ATTEMPTS" in dead["reason"]
    assert await pending(fake_redis) == 0
    assert await count_rows() == 0

