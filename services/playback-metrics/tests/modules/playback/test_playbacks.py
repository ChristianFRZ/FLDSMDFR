import asyncio
from uuid import uuid4

from playback_metrics.modules.playback import public
from tests.plays import progress_play, record_play


async def post_play(client, user, playback_id, song, seconds=12):
    return await record_play(user, song, seconds, playback_id=playback_id)


async def events(limit=500):
    return await public.events_since(0, limit)


async def test_hundred_concurrent_duplicates(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    results = await asyncio.gather(*[post_play(client, listener, pid, song) for _ in range(100)])
    assert sorted(set(results)) == ["created", "duplicate"]
    assert len([e for e in await events() if str(e.playback_id) == pid]) == 1
    assert await public.duplicates_discarded() == 99


async def test_duplicate_is_reported_as_duplicate_and_new_as_created(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    assert await post_play(client, listener, pid, song) == "created"
    assert await post_play(client, listener, pid, song) == "duplicate"


async def test_history_keeps_deleted_song_as_null(client, listener, make_song, fake_catalog):
    song = await make_song()
    await post_play(client, listener, str(uuid4()), song)
    fake_catalog.delete(song)
    r = await client.get("/api/playbacks/history", headers=listener.headers)
    assert r.json()["items"][0]["song"] is None


async def test_progress_only_increases(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    await post_play(client, listener, pid, song)
    assert await progress_play(listener, pid, 60) == "progress"
    assert await progress_play(listener, pid, 30) == "progress"
    assert (await events())[0].listened_seconds == 60


async def test_progress_not_counted_as_duplicate(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    await post_play(client, listener, pid, song)
    await progress_play(listener, pid, 60)
    assert await public.duplicates_discarded() == 0
    assert len(await events()) == 1


async def test_progress_of_foreign_playback_is_discarded(client, listener, make_user, make_song):
    other, song, pid = await make_user(), await make_song(), str(uuid4())
    await post_play(client, listener, pid, song)
    assert await progress_play(other, pid, 60) == "discarded"
    assert (await events())[0].listened_seconds == 12


async def test_progress_of_unknown_playback_is_discarded(client, listener):
    assert await progress_play(listener, uuid4(), 60) == "discarded"


async def test_history_only_own(client, listener, make_user, make_song):
    other, mine, theirs = await make_user(), await make_song(title="Mía"), await make_song(title="Ajena")
    await post_play(client, listener, str(uuid4()), mine)
    await post_play(client, other, str(uuid4()), theirs)
    r = await client.get("/api/playbacks/history", headers=listener.headers)
    assert [i["song"]["title"] for i in r.json()["items"]] == ["Mía"]
    assert r.json()["total"] == 1


async def test_events_since_uses_cursor(client, listener, make_song):
    song = await make_song()
    for _ in range(3):
        await post_play(client, listener, str(uuid4()), song)
    first = await public.events_since(0, 2)
    rest = await public.events_since(first[-1].seq, 10)
    assert len(first) == 2
    assert len(rest) == 1


async def test_retention_counts_thresholds(client, listener, make_song):
    song = await make_song()
    for seconds in (10, 100, 200):
        await post_play(client, listener, str(uuid4()), song, seconds=seconds)
    stats = await public.retention_for_songs([song.id], {song.id: 200})
    assert (stats.at_10s, stats.at_50, stats.at_100) == (3, 2, 1)


async def test_retention_counts_end_with_fractional_duration(client, listener, make_song):
    """El progreso se guarda en segundos enteros y la duración real de un MP3 casi nunca lo es."""
    song = await make_song()
    for seconds in (39, 40):
        await post_play(client, listener, str(uuid4()), song, seconds=seconds)
    stats = await public.retention_for_songs([song.id], {song.id: 40.05})
    assert stats.at_100 == 1


async def test_retention_empty_without_songs():
    stats = await public.retention_for_songs([], {})
    assert (stats.at_10s, stats.at_50, stats.at_100) == (0, 0, 0)
