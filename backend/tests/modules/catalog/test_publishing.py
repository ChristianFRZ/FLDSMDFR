import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import respx
from sqlalchemy import func, select

from app.core.db import session_scope
from app.core.scheduler import periodic
from app.modules.catalog.models import PublishedEvent, Song
from app.modules.catalog.publishing import publish_due_tracks
from tests.media import mp3

PAST = datetime.now(UTC) - timedelta(minutes=5)
FUTURE = datetime.now(UTC) + timedelta(days=1)


async def count_events():
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(PublishedEvent))


async def status_of(song):
    async with session_scope() as session:
        return await session.scalar(select(Song.status).where(Song.id == song.id))


async def test_publish_due_only(make_song):
    due = await make_song(title="A", status="scheduled", publish_at=PAST)
    later = await make_song(title="B", status="scheduled", publish_at=FUTURE)
    assert await publish_due_tracks() == 1
    assert await status_of(due) == "published"
    assert await status_of(later) == "scheduled"


async def test_published_at_set(make_song):
    song = await make_song(status="scheduled", publish_at=PAST)
    await publish_due_tracks()
    async with session_scope() as session:
        assert await session.scalar(select(Song.published_at).where(Song.id == song.id)) is not None


async def test_two_workers_publish_once(make_song):
    await make_song(status="scheduled", publish_at=PAST)
    counts = await asyncio.gather(publish_due_tracks(), publish_due_tracks())
    assert sum(counts) == 1
    assert await count_events() == 1


async def test_many_tracks_two_workers_each_once(make_song):
    for i in range(20):
        await make_song(title=f"P{i}", status="scheduled", publish_at=PAST)
    counts = await asyncio.gather(publish_due_tracks(), publish_due_tracks(), publish_due_tracks())
    assert sum(counts) == 20
    assert await count_events() == 20


async def test_manual_publish_records_event_once(client, composer):
    r = await client.post(
        "/api/composer/tracks",
        data={"title": "T", "genre": "rock", "license": "CC"},
        files={"audio": ("a.mp3", mp3())},
        headers=composer.headers,
    )
    url = f"/api/composer/tracks/{r.json()['id']}"
    await client.post(f"{url}/publish", headers=composer.headers)
    await client.post(f"{url}/hide", headers=composer.headers)
    await client.post(f"{url}/publish", headers=composer.headers)
    assert await count_events() == 1


async def test_hide_requires_reason(client, admin, make_song):
    song = await make_song()
    r = await client.post(f"/api/admin/songs/{song.id}/hide", json={}, headers=admin.headers)
    assert r.status_code == 422


async def test_hide_audits_reason_and_removes_from_catalog(client, admin, listener, make_song):
    song = await make_song()
    r = await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "derechos"}, headers=admin.headers)
    assert r.status_code == 200
    assert (await client.get("/api/songs", headers=listener.headers)).json()["total"] == 0
    row = (await client.get("/api/admin/audit?action=hide_song", headers=admin.headers)).json()["items"][0]
    assert row["detail"]["reason"] == "derechos"
    assert row["target_id"] == str(song.id)


async def test_admin_can_hide_jamendo(client, admin, make_song):
    song = await make_song(artist="J", source="jamendo", jamendo_id="1")
    r = await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    assert r.status_code == 200


async def test_restore(client, admin, listener, make_song):
    song = await make_song()
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    r = await client.post(f"/api/admin/songs/{song.id}/restore", headers=admin.headers)
    assert r.status_code == 200
    assert (await client.get("/api/songs", headers=listener.headers)).json()["total"] == 1


async def test_composer_cannot_restore_admin_hidden(client, admin, composer):
    r = await client.post(
        "/api/composer/tracks",
        data={"title": "T", "genre": "rock", "license": "CC"},
        files={"audio": ("a.mp3", mp3())},
        headers=composer.headers,
    )
    song_id = r.json()["id"]
    await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    await client.post(f"/api/admin/songs/{song_id}/hide", json={"reason": "x"}, headers=admin.headers)
    r = await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "hidden_by_admin"


async def test_hide_403_for_composer(client, composer, make_song):
    song = await make_song()
    r = await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=composer.headers)
    assert r.status_code == 403


async def test_admin_lists_hidden_songs(client, admin, make_song):
    await make_song(status="hidden")
    await make_song(title="Otra")
    r = (await client.get("/api/admin/songs?status=hidden", headers=admin.headers)).json()
    assert r["total"] == 1


async def test_scheduler_survives_failing_task():
    calls = []

    async def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("falla")

    task = periodic("prueba", 0.01, flaky)
    await asyncio.sleep(0.06)
    task.cancel()
    assert len(calls) >= 2


@respx.mock
async def test_expired_audio_url_is_refreshed_once(client, listener, make_song):
    song = await make_song(artist="J", source="jamendo", jamendo_id="9", audio_url="https://audio.example/viejo")
    respx.get("https://audio.example/viejo").mock(return_value=httpx.Response(403))
    respx.get("https://api.jamendo.com/v3.0/tracks/").mock(
        return_value=httpx.Response(
            200,
            json={
                "headers": {"status": "success"},
                "results": [
                    {"id": "9", "name": "x", "artist_id": "1", "audio": "https://audio.example/nuevo"},
                ],
            },
        )
    )
    new = respx.get("https://audio.example/nuevo").mock(
        return_value=httpx.Response(206, content=b"abc", headers={"Content-Range": "bytes 0-2/3"})
    )
    r = await client.get(f"/api/songs/{song.id}/stream", headers={**listener.headers, "Range": "bytes=0-2"})
    assert r.status_code == 206
    assert new.called
    async with session_scope() as session:
        assert await session.scalar(select(Song.audio_url).where(Song.id == song.id)) == "https://audio.example/nuevo"


async def upload_track(client, composer, **fields):
    r = await client.post(
        "/api/composer/tracks",
        data={"title": "T", "genre": "rock", "license": "CC", **fields},
        files={"audio": ("a.mp3", mp3())},
        headers=composer.headers,
    )
    return r.json()["id"]


async def hide_and_restore(client, admin, song_id):
    await client.post(f"/api/admin/songs/{song_id}/hide", json={"reason": "x"}, headers=admin.headers)
    return await client.post(f"/api/admin/songs/{song_id}/restore", headers=admin.headers)


async def song_state(song_id):
    async with session_scope() as session:
        song = await session.get(Song, song_id)
        return song.status, song.publish_at, song.published_at, song.hidden_by_admin


async def test_restore_keeps_schedule(client, admin, composer):
    song_id = await upload_track(client, composer, publish_at=FUTURE.isoformat())
    assert (await hide_and_restore(client, admin, song_id)).status_code == 200
    status, publish_at, published_at, hidden_by_admin = await song_state(song_id)
    assert (status, published_at, hidden_by_admin) == ("scheduled", None, False)
    assert publish_at == FUTURE


async def test_restore_keeps_draft(client, admin, composer):
    song_id = await upload_track(client, composer)
    await hide_and_restore(client, admin, song_id)
    assert (await song_state(song_id))[0] == "draft"
    assert (await song_state(song_id))[2] is None


async def test_restore_published_keeps_date(client, admin, composer):
    song_id = await upload_track(client, composer)
    await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    before = (await song_state(song_id))[2]
    await hide_and_restore(client, admin, song_id)
    assert (await song_state(song_id))[0] == "published"
    assert (await song_state(song_id))[2] == before


async def test_restore_refuses_track_the_composer_hid(client, admin, composer):
    song_id = await upload_track(client, composer)
    await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    await client.post(f"/api/composer/tracks/{song_id}/hide", headers=composer.headers)
    r = await client.post(f"/api/admin/songs/{song_id}/restore", headers=admin.headers)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "not_hidden_by_admin"
    assert (await song_state(song_id))[0] == "hidden"


async def test_restore_returns_to_composer_hidden(client, admin, composer):
    song_id = await upload_track(client, composer)
    await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    await client.post(f"/api/composer/tracks/{song_id}/hide", headers=composer.headers)
    await hide_and_restore(client, admin, song_id)
    status, _, _, hidden_by_admin = await song_state(song_id)
    assert (status, hidden_by_admin) == ("hidden", False)


async def test_admin_list_says_who_hid(client, admin, composer):
    song_id = await upload_track(client, composer)
    await client.post(f"/api/admin/songs/{song_id}/hide", json={"reason": "x"}, headers=admin.headers)
    items = (await client.get("/api/admin/songs", headers=admin.headers)).json()["items"]
    assert items[0]["hidden_by_admin"] is True
