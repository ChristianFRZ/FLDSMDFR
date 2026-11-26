from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text

from meloxo_common.db import get_engine


def now():
    return datetime.now(UTC)


async def follow(client, user, artist_id):
    return await client.put(f"/api/follows/{artist_id}", headers=user.headers)


async def notices(client, user):
    r = await client.get("/api/notices", headers=user.headers)
    assert r.status_code == 200, r.text
    return r.json()


async def followed_with_release(client, listener, composer, make_song, title="Nueva"):
    old = await make_song(title="Vieja", owner=composer.id, published_at=now() - timedelta(days=30))
    await follow(client, listener, old.artist_id)
    return await make_song(title=title, owner=composer.id, published_at=now() + timedelta(seconds=1))


async def test_notices_list_releases_without_calling_catalog(client, listener, composer, make_song, fake_catalog):
    await followed_with_release(client, listener, composer, make_song)
    fake_catalog.calls.clear()
    body = await notices(client, listener)
    assert [i["song"]["title"] for i in body["items"]] == ["Nueva"]
    assert fake_catalog.calls == []


async def test_notices_work_when_catalog_is_down(client, listener, composer, make_song, fake_catalog):
    await followed_with_release(client, listener, composer, make_song)
    fake_catalog.down = True
    body = await notices(client, listener)
    assert body["degraded"] is False
    assert [i["song"]["title"] for i in body["items"]] == ["Nueva"]


async def test_release_before_following_does_not_notify(client, listener, composer, make_song):
    song = await make_song(owner=composer.id, published_at=now() - timedelta(days=1))
    await follow(client, listener, song.artist_id)
    assert (await notices(client, listener))["unread"] == 0


async def test_release_before_last_seen_does_not_notify(client, listener, composer, make_song):
    old = await make_song(title="Vieja", owner=composer.id, published_at=now() - timedelta(days=30))
    await follow(client, listener, old.artist_id)
    await make_song(title="Reciente", owner=composer.id, published_at=now())
    assert (await notices(client, listener))["unread"] == 1
    await client.post("/api/notices/seen", headers=listener.headers)
    assert (await notices(client, listener))["unread"] == 0


async def test_other_artists_releases_do_not_notify(client, listener, composer, make_song):
    await followed_with_release(client, listener, composer, make_song)
    await make_song(title="Ajena", artist="Otro Artista", published_at=now() + timedelta(seconds=2))
    assert [i["song"]["title"] for i in (await notices(client, listener))["items"]] == ["Nueva"]


async def test_malformed_stored_song_is_skipped(client, listener, composer, make_song):
    first = await followed_with_release(client, listener, composer, make_song)
    async with get_engine().begin() as conn:
        await conn.execute(
            text("INSERT INTO release_events (song_id, artist_id, published_at, song) VALUES (:s, :a, :p, '{\"roto\": true}')"),
            {"s": uuid4(), "a": first.artist_id, "p": now() + timedelta(seconds=3)},
        )
    body = await notices(client, listener)
    assert [i["song"]["title"] for i in body["items"]] == ["Nueva"]


async def test_hidden_after_publish_still_listed(client, listener, composer, make_song, fake_catalog):
    """Decisión del diseño (§6, camino 1): la copia local no cambia aunque catálogo oculte la pista."""
    song = await followed_with_release(client, listener, composer, make_song)
    fake_catalog.hide(song)
    assert [i["song"]["title"] for i in (await notices(client, listener))["items"]] == ["Nueva"]
