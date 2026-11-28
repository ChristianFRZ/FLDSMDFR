from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fakeredis import aioredis as fakeredis

from meloxo_common import track_events as te


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


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


def test_round_trip():
    original = event()
    assert te.from_fields(te.to_fields(original)) == original


@pytest.mark.parametrize("field", ["song_id", "artist_id", "published_at", "song"])
def test_missing_field_raises_value_error(field):
    fields = te.to_fields(event())
    del fields[field]
    with pytest.raises(ValueError, match=field):
        te.from_fields(fields)


def test_bad_uuid_and_bad_date_raise():
    for key, value in (("song_id", "no-es-uuid"), ("artist_id", "tampoco"), ("published_at", "ayer")):
        fields = te.to_fields(event())
        fields[key] = value
        with pytest.raises(ValueError):
            te.from_fields(fields)


def test_song_that_is_not_a_json_object_raises():
    for bad in ("no es json", "[1, 2]", '"texto"'):
        fields = te.to_fields(event())
        fields["song"] = bad
        with pytest.raises(ValueError):
            te.from_fields(fields)


def test_song_id_mismatch_raises():
    fields = te.to_fields(event())
    fields["song_id"] = str(uuid4())
    with pytest.raises(ValueError, match="song_id"):
        te.from_fields(fields)


async def test_enqueue_adds_to_the_stream(redis):
    original = event()
    await te.enqueue(redis, original)
    [(_, fields)] = await redis.xrange(te.STREAM)
    assert te.from_fields(fields) == original


async def test_ensure_group_is_idempotent(redis):
    await te.ensure_group(redis)
    await te.ensure_group(redis)
    assert [g["name"] for g in await redis.xinfo_groups(te.STREAM)] == [te.GROUP]


async def test_send_to_dlq_keeps_fields_and_adds_reason(redis):
    fields = {"song_id": "roto"}
    await te.send_to_dlq(redis, "1-0", fields, "UUID inválido")
    [(_, dead)] = await redis.xrange(te.DLQ_STREAM)
    assert dead == {"song_id": "roto", "reason": "UUID inválido", "original_id": "1-0"}
