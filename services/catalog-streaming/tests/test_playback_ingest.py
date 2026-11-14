import asyncio
import time
from uuid import uuid4

import pytest

from meloxo_common import playback_queue as q
from meloxo_common.redis_client import override_redis


async def entries(redis):
    return [q.from_fields(fields) for _, fields in await redis.xrange(q.STREAM)]


def body(song, **kw):
    return {"playback_id": str(uuid4()), "song_id": str(song.id), "listened_seconds": 12, **kw}


async def test_post_enqueues_record_and_returns_202(client, fake_redis, listener, make_song):
    song = await make_song()
    data = body(song)
    r = await client.post("/api/playbacks", json=data, headers=listener.headers)
    assert r.status_code == 202
    assert r.json() == {"playback_id": data["playback_id"]}
    [event] = await entries(fake_redis)
    assert (event.type, str(event.playback_id), str(event.song_id), event.listened_seconds) == (
        "record",
        data["playback_id"],
        str(song.id),
        12,
    )


async def test_post_requires_session(client, fake_redis, make_song):
    song = await make_song()
    r = await client.post("/api/playbacks", json=body(song))
    assert r.status_code == 401
    assert await entries(fake_redis) == []


async def test_post_unknown_song_is_404_and_enqueues_nothing(client, fake_redis, listener):
    data = {"playback_id": str(uuid4()), "song_id": str(uuid4()), "listened_seconds": 12}
    r = await client.post("/api/playbacks", json=data, headers=listener.headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "song_not_found"
    assert await entries(fake_redis) == []


@pytest.mark.parametrize("seconds", [-1, 86401])
async def test_post_invalid_seconds_is_422(client, fake_redis, listener, make_song, seconds):
    song = await make_song()
    r = await client.post("/api/playbacks", json=body(song, listened_seconds=seconds), headers=listener.headers)
    assert r.status_code == 422
    assert await entries(fake_redis) == []


async def test_user_id_comes_from_token_not_body(client, fake_redis, listener, make_song):
    song = await make_song()
    r = await client.post("/api/playbacks", json=body(song, user_id=str(uuid4())), headers=listener.headers)
    assert r.status_code == 202
    [event] = await entries(fake_redis)
    assert str(event.user_id) == listener.id


async def test_patch_enqueues_progress_and_returns_202(client, fake_redis, listener):
    pid = uuid4()
    r = await client.patch(f"/api/playbacks/{pid}/progress", json={"listened_seconds": 60}, headers=listener.headers)
    assert r.status_code == 202
    assert r.json() == {"playback_id": str(pid)}
    [event] = await entries(fake_redis)
    assert (event.type, event.playback_id, event.listened_seconds, event.song_id) == ("progress", pid, 60, None)
    assert str(event.user_id) == listener.id


async def test_patch_requires_session(client, fake_redis):
    r = await client.patch(f"/api/playbacks/{uuid4()}/progress", json={"listened_seconds": 60})
    assert r.status_code == 401


class Failing:
    def __init__(self, hang: bool):
        self.hang = hang

    async def xadd(self, *args, **kwargs):
        if self.hang:
            await asyncio.sleep(30)
        raise ConnectionError("Redis caído")


@pytest.mark.parametrize("hang", [False, True], ids=["error", "hung"])
async def test_redis_down_returns_503_upstream_unavailable_quickly(client, listener, make_song, hang):
    song = await make_song()
    override_redis(Failing(hang))
    start = time.monotonic()
    r = await client.post("/api/playbacks", json=body(song), headers=listener.headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"
    assert time.monotonic() - start < 2
    override_redis(None)


async def test_redis_disabled_returns_503(client, listener, make_song):
    song = await make_song()
    r = await client.post("/api/playbacks", json=body(song), headers=listener.headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"
