from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from meloxo_common import playback_queue as q
from meloxo_common.db import session_scope
from playback_metrics.modules.playback import consumer, service
from playback_metrics.modules.playback.models import Playback, PlaybackCounter


def event(type="record", **kw):
    data = dict(
        type=type,
        user_id=uuid4(),
        playback_id=uuid4(),
        listened_seconds=12,
        song_id=uuid4() if type == "record" else None,
        received_at=datetime.now(UTC).isoformat(),
    )
    data.update(kw)
    return q.QueuedEvent(**data)


async def run(redis, **kw) -> int:
    return await consumer.consume_once(redis, "test", block_ms=10, retry_delay=0, **kw)


async def plays() -> int:
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(Playback))


async def listened(playback_id) -> int:
    async with session_scope() as session:
        return await session.scalar(select(Playback.listened_seconds).where(Playback.playback_id == playback_id))


async def counter(key: str) -> int:
    async with session_scope() as session:
        return await session.scalar(select(PlaybackCounter.value).where(PlaybackCounter.key == key)) or 0


async def pending(redis) -> int:
    return (await redis.xpending(q.STREAM, q.GROUP))["pending"]


async def test_record_event_is_applied_and_acked(fake_redis):
    await q.ensure_group(fake_redis)
    await q.enqueue(fake_redis, event())
    assert await run(fake_redis) == 1
    assert await plays() == 1
    assert await pending(fake_redis) == 0


async def test_progress_after_record_raises_listened_seconds(fake_redis):
    await q.ensure_group(fake_redis)
    first = event()
    await q.enqueue(fake_redis, first)
    await q.enqueue(fake_redis, event("progress", user_id=first.user_id, playback_id=first.playback_id, listened_seconds=60))
    await run(fake_redis)
    assert await listened(first.playback_id) == 60
    assert await counter("events_discarded") == 0


async def test_resent_playback_id_counts_one_play_and_duplicates(fake_redis):
    await q.ensure_group(fake_redis)
    same = event()
    for _ in range(100):
        await q.enqueue(fake_redis, same)
    while await run(fake_redis, count=30):
        pass
    assert await plays() == 1
    assert await counter(service.DUPLICATES) == 99


async def test_redelivered_message_does_not_count_twice(fake_redis):
    await q.ensure_group(fake_redis)
    ev = event()
    await q.enqueue(fake_redis, ev)
    # Un consumidor lo lee y lo guarda, pero cae antes del XACK.
    [(_, [(_, fields)])] = await fake_redis.xreadgroup(q.GROUP, "muerto", {q.STREAM: ">"}, count=1)
    async with session_scope() as session:
        assert await service.apply_event(session, q.from_fields(fields)) == "created"
    assert await pending(fake_redis) == 1
    await run(fake_redis, min_idle_ms=0)
    assert await plays() == 1
    assert await pending(fake_redis) == 0


async def test_transient_db_error_is_not_acked_and_is_retried(fake_redis, monkeypatch):
    await q.ensure_group(fake_redis)
    ev = event()
    await q.enqueue(fake_redis, ev)
    real = service.apply_event
    calls = {"n": 0}

    async def flaky(session, e):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("base caída")
        return await real(session, e)

    monkeypatch.setattr(service, "apply_event", flaky)
    await run(fake_redis)
    assert await plays() == 0 and await pending(fake_redis) == 1
    await run(fake_redis)
    assert await plays() == 1 and await pending(fake_redis) == 0


async def test_failed_record_blocks_later_events_so_order_is_kept(fake_redis, monkeypatch):
    await q.ensure_group(fake_redis)
    first = event()
    await q.enqueue(fake_redis, first)
    await q.enqueue(fake_redis, event("progress", user_id=first.user_id, playback_id=first.playback_id, listened_seconds=40))
    real = service.apply_event
    failed = []

    async def flaky(session, e):
        if e.type == "record" and not failed:
            failed.append(1)
            raise ConnectionError("base caída")
        return await real(session, e)

    monkeypatch.setattr(service, "apply_event", flaky)
    await run(fake_redis)
    await run(fake_redis)
    assert await listened(first.playback_id) == 40
    assert await counter("events_discarded") == 0


async def test_invalid_message_is_acked_and_discarded(fake_redis):
    await q.ensure_group(fake_redis)
    await fake_redis.xadd(q.STREAM, {"type": "record", "basura": "1"})
    await q.enqueue(fake_redis, event())
    await run(fake_redis)
    assert await counter("events_discarded") == 1
    assert await plays() == 1
    assert await pending(fake_redis) == 0


async def test_progress_for_foreign_or_missing_playback_is_discarded(fake_redis):
    await q.ensure_group(fake_redis)
    mine = event()
    await q.enqueue(fake_redis, mine)
    await q.enqueue(fake_redis, event("progress", playback_id=mine.playback_id, listened_seconds=99))  # otro usuario
    await q.enqueue(fake_redis, event("progress", listened_seconds=99))  # no existe
    await run(fake_redis)
    assert await listened(mine.playback_id) == 12
    assert await counter("events_discarded") == 2


async def test_consumer_does_not_check_catalog(fake_redis, fake_catalog):
    fake_catalog.down = True
    await q.ensure_group(fake_redis)
    await q.enqueue(fake_redis, event())
    await run(fake_redis)
    assert await plays() == 1


async def test_play_keeps_the_time_it_was_received_not_the_time_it_was_applied(fake_redis):
    """Tras una caída de playback-metrics, lo escuchado durante ella no debe parecer escuchado al volver."""
    from datetime import timedelta

    await q.ensure_group(fake_redis)
    earlier = datetime.now(UTC) - timedelta(hours=3)
    ev = event(received_at=earlier.isoformat())
    await q.enqueue(fake_redis, ev)
    await run(fake_redis)
    async with session_scope() as session:
        started = await session.scalar(select(Playback.started_at).where(Playback.playback_id == ev.playback_id))
    assert abs((started - earlier).total_seconds()) < 1
