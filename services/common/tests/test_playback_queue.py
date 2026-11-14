from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fakeredis import aioredis as fakeredis

from meloxo_common import playback_queue as q


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


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.mark.parametrize("kind", ["record", "progress"])
def test_roundtrip_of_fields(kind):
    original = event(kind)
    assert q.from_fields(q.to_fields(original)) == original


def test_from_fields_rejects_missing_field():
    fields = q.to_fields(event())
    del fields["playback_id"]
    with pytest.raises(ValueError):
        q.from_fields(fields)


def test_from_fields_rejects_unknown_type():
    fields = q.to_fields(event())
    fields["type"] = "borrar"
    with pytest.raises(ValueError):
        q.from_fields(fields)


def test_from_fields_rejects_bad_values():
    for key, value in [("user_id", "no-es-uuid"), ("listened_seconds", "mucho"), ("listened_seconds", "-3")]:
        fields = q.to_fields(event())
        fields[key] = value
        with pytest.raises(ValueError):
            q.from_fields(fields)


def test_record_requires_song_id():
    fields = q.to_fields(event())
    del fields["song_id"]
    with pytest.raises(ValueError):
        q.from_fields(fields)


async def test_enqueue_adds_to_stream_and_trims(redis):
    for _ in range(3):
        await q.enqueue(redis, event())
    assert await redis.xlen(q.STREAM) == 3
    entries = await redis.xrange(q.STREAM)
    assert q.from_fields(entries[0][1]).type == "record"


async def test_ensure_group_is_idempotent(redis):
    await q.ensure_group(redis)
    await q.ensure_group(redis)
    groups = await redis.xinfo_groups(q.STREAM)
    assert [g["name"] for g in groups] == [q.GROUP]
