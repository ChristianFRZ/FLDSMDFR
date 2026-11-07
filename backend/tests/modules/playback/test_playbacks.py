import asyncio
from uuid import uuid4

from app.modules.playback import public


async def post_play(client, user, playback_id, song, seconds=12):
    return await client.post(
        "/api/playbacks",
        json={"playback_id": playback_id, "song_id": str(song.id), "listened_seconds": seconds},
        headers=user.headers,
    )


async def events(limit=500):
    return await public.events_since(0, limit)


async def test_hundred_concurrent_duplicates(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    results = await asyncio.gather(*[post_play(client, listener, pid, song) for _ in range(100)])
    assert sorted({r.status_code for r in results}) == [200, 201]
    assert len([e for e in await events() if str(e.playback_id) == pid]) == 1
    assert await public.duplicates_discarded() == 99


async def test_duplicate_returns_200_new_returns_201(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    assert (await post_play(client, listener, pid, song)).status_code == 201
    assert (await post_play(client, listener, pid, song)).status_code == 200


async def test_unknown_song_404(client, listener):
    r = await client.post(
        "/api/playbacks",
        json={"playback_id": str(uuid4()), "song_id": str(uuid4()), "listened_seconds": 12},
        headers=listener.headers,
    )
    assert r.status_code == 404


async def test_negative_seconds_rejected(client, listener, make_song):
    r = await post_play(client, listener, str(uuid4()), await make_song(), seconds=-1)
    assert r.status_code == 422


async def test_absurd_seconds_rejected(client, listener, make_song):
    r = await post_play(client, listener, str(uuid4()), await make_song(), seconds=10**12)
    assert r.status_code == 422


async def test_history_keeps_deleted_song_as_null(client, listener, make_song):
    from sqlalchemy import delete

    from app.core.db import session_scope
    from app.modules.catalog.models import Song

    song = await make_song()
    await post_play(client, listener, str(uuid4()), song)
    async with session_scope() as session:
        await session.execute(delete(Song).where(Song.id == song.id))
    r = await client.get("/api/playbacks/history", headers=listener.headers)
    assert r.json()["items"][0]["song"] is None


async def test_progress_only_increases(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    await post_play(client, listener, pid, song)
    url = f"/api/playbacks/{pid}/progress"
    assert (await client.patch(url, json={"listened_seconds": 60}, headers=listener.headers)).status_code == 200
    r = await client.patch(url, json={"listened_seconds": 30}, headers=listener.headers)
    assert r.json()["listened_seconds"] == 60
    assert (await events())[0].listened_seconds == 60


async def test_progress_not_counted_as_duplicate(client, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    await post_play(client, listener, pid, song)
    await client.patch(f"/api/playbacks/{pid}/progress", json={"listened_seconds": 60}, headers=listener.headers)
    assert await public.duplicates_discarded() == 0
    assert len(await events()) == 1


async def test_progress_of_foreign_playback_403(client, listener, make_user, make_song):
    other, song, pid = await make_user(), await make_song(), str(uuid4())
    await post_play(client, listener, pid, song)
    r = await client.patch(f"/api/playbacks/{pid}/progress", json={"listened_seconds": 60}, headers=other.headers)
    assert r.status_code == 403


async def test_progress_of_unknown_playback_404(client, listener):
    r = await client.patch(f"/api/playbacks/{uuid4()}/progress", json={"listened_seconds": 60}, headers=listener.headers)
    assert r.status_code == 404


async def test_history_only_own(client, listener, make_user, make_song):
    other, mine, theirs = await make_user(), await make_song(title="Mía"), await make_song(title="Ajena")
    await post_play(client, listener, str(uuid4()), mine)
    await post_play(client, other, str(uuid4()), theirs)
    r = await client.get("/api/playbacks/history", headers=listener.headers)
    assert [i["song"]["title"] for i in r.json()["items"]] == ["Mía"]
    assert r.json()["total"] == 1


async def test_user_from_token(client, listener, make_user, make_song):
    other, song = await make_user(), await make_song()
    await client.post(
        "/api/playbacks",
        json={"playback_id": str(uuid4()), "song_id": str(song.id), "listened_seconds": 12, "user_id": other.id},
        headers=listener.headers,
    )
    assert str((await events())[0].user_id) == listener.id


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
