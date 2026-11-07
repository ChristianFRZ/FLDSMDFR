from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.social import service


def now():
    return datetime.now(UTC)


async def follow(client, user, artist_id):
    return await client.put(f"/api/follows/{artist_id}", headers=user.headers)


async def notices(client, user):
    r = await client.get("/api/notices", headers=user.headers)
    assert r.status_code == 200, r.text
    return r.json()


async def publish_after_follow(client, listener, composer, make_song, title="Nueva"):
    first = await make_song(title="Vieja", owner=composer.id, published_at=now() - timedelta(days=30))
    await follow(client, listener, first.artist_id)
    return await make_song(title=title, owner=composer.id, published_at=now() + timedelta(seconds=1))


async def test_favorite_idempotent(client, listener, make_song):
    song = await make_song()
    url = f"/api/favorites/{song.id}"
    assert (await client.put(url, headers=listener.headers)).status_code == 204
    assert (await client.put(url, headers=listener.headers)).status_code == 204
    r = await client.get("/api/favorites", headers=listener.headers)
    assert r.json()["total"] == 1


async def test_favorite_unknown_song_404(client, listener):
    assert (await client.put(f"/api/favorites/{uuid4()}", headers=listener.headers)).status_code == 404


async def test_unfavorite(client, listener, make_song):
    song = await make_song()
    url = f"/api/favorites/{song.id}"
    await client.put(url, headers=listener.headers)
    assert (await client.delete(url, headers=listener.headers)).status_code == 204
    assert (await client.delete(url, headers=listener.headers)).status_code == 204
    assert (await client.get("/api/favorites", headers=listener.headers)).json()["items"] == []


async def test_favorites_are_private(client, listener, make_user, make_song):
    other, song = await make_user(), await make_song()
    await client.put(f"/api/favorites/{song.id}", headers=listener.headers)
    assert (await client.get("/api/favorites", headers=other.headers)).json()["total"] == 0


async def test_hidden_favorite_marked_unavailable(client, admin, listener, make_song):
    song = await make_song()
    await client.put(f"/api/favorites/{song.id}", headers=listener.headers)
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    item = (await client.get("/api/favorites", headers=listener.headers)).json()["items"][0]
    assert item["available"] is False


async def test_deleted_favorite_marked_unavailable(client, composer, listener, make_song):
    song = await make_song(owner=composer.id)
    kept = await make_song(title="Sigue")
    await client.put(f"/api/favorites/{song.id}", headers=listener.headers)
    await client.put(f"/api/favorites/{kept.id}", headers=listener.headers)
    await client.delete(f"/api/composer/tracks/{song.id}", headers=composer.headers)
    body = (await client.get("/api/favorites", headers=listener.headers)).json()
    assert body["total"] == len(body["items"]) == 2
    gone = next(i for i in body["items"] if i["id"] == str(song.id))
    assert gone["available"] is False


async def test_follow_jamendo_and_composer_artists(client, listener, composer, make_song):
    jamendo = await make_song(artist="Remoto", source="jamendo")
    local = await make_song(artist="Local", owner=composer.id)
    assert (await follow(client, listener, jamendo.artist_id)).status_code == 204
    assert (await follow(client, listener, local.artist_id)).status_code == 204
    assert (await follow(client, listener, local.artist_id)).status_code == 204
    names = {a["name"] for a in (await client.get("/api/follows", headers=listener.headers)).json()}
    assert names == {"Remoto", "Local"}


async def test_follow_unknown_artist_404(client, listener):
    assert (await follow(client, listener, uuid4())).status_code == 404


async def test_published_track_creates_notice_for_followers(client, listener, composer, make_song):
    await publish_after_follow(client, listener, composer, make_song)
    body = await notices(client, listener)
    assert body["unread"] == 1
    assert body["degraded"] is False
    assert body["items"][0]["type"] == "release"
    assert body["items"][0]["song"]["title"] == "Nueva"


async def test_older_tracks_do_not_notify_new_follower(client, listener, composer, make_song):
    song = await make_song(owner=composer.id, published_at=now() - timedelta(days=1))
    await follow(client, listener, song.artist_id)
    assert (await notices(client, listener))["unread"] == 0


async def test_jamendo_import_creates_no_notice(client, listener, make_song):
    first = await make_song(artist="Remoto", source="jamendo", published_at=now() - timedelta(days=1))
    await follow(client, listener, first.artist_id)
    await make_song(artist="Remoto", source="jamendo", published_at=now() + timedelta(seconds=1))
    assert (await notices(client, listener))["unread"] == 0


async def test_notices_computed_on_read_and_seen_clears(client, listener, composer, make_song):
    await publish_after_follow(client, listener, composer, make_song)
    assert (await client.post("/api/notices/seen", headers=listener.headers)).status_code == 204
    song = await make_song(title="Otra", owner=composer.id, published_at=now() + timedelta(seconds=5))
    titles = [i["song"]["title"] for i in (await notices(client, listener))["items"]]
    assert song.title in titles


async def test_seen_hides_what_was_published_before(client, listener, composer, make_song):
    song = await make_song(owner=composer.id, published_at=now() - timedelta(days=30))
    await follow(client, listener, song.artist_id)
    await make_song(title="Reciente", owner=composer.id, published_at=now())
    assert (await notices(client, listener))["unread"] == 1
    await client.post("/api/notices/seen", headers=listener.headers)
    assert (await notices(client, listener))["unread"] == 0


async def test_unfollowed_artist_no_notice(client, listener, composer, make_song):
    song = await publish_after_follow(client, listener, composer, make_song)
    await client.delete(f"/api/follows/{song.artist_id}", headers=listener.headers)
    assert (await notices(client, listener))["unread"] == 0


async def test_catalog_down_notices_still_show_invites(client, listener, composer, make_song, monkeypatch):
    await publish_after_follow(client, listener, composer, make_song)

    async def broken(*_):
        raise RuntimeError("catálogo caído")

    monkeypatch.setattr(service, "published_since", broken)
    body = await notices(client, listener)
    assert body["degraded"] is True
    assert body["items"] == []


async def test_releases_include_scheduled_with_date(client, listener, composer, make_song):
    first = await make_song(owner=composer.id)
    await follow(client, listener, first.artist_id)
    when = now() + timedelta(days=3)
    await make_song(title="Pronto", owner=composer.id, status="scheduled", publish_at=when)
    body = (await client.get("/api/releases", headers=listener.headers)).json()
    item = body["scheduled"][0]
    assert item["title"] == "Pronto"
    assert item["publish_at"]
    assert not any("audio" in key or "stream" in key for key in item)


async def test_releases_only_followed(client, listener, composer, make_song):
    await make_song(title="Pronto", owner=composer.id, status="scheduled", publish_at=now() + timedelta(days=3))
    body = (await client.get("/api/releases", headers=listener.headers)).json()
    assert body["scheduled"] == []


async def test_releases_list_recent_published(client, listener, composer, make_song):
    song = await make_song(owner=composer.id, published_at=now())
    await follow(client, listener, song.artist_id)
    body = (await client.get("/api/releases", headers=listener.headers)).json()
    assert [i["song"]["id"] for i in body["published"]] == [str(song.id)]


async def test_favorite_ids(client, listener, make_song):
    song = await make_song()
    await client.put(f"/api/favorites/{song.id}", headers=listener.headers)
    r = await client.get("/api/favorites/ids", headers=listener.headers)
    assert r.json() == [str(song.id)]


async def test_followed_ids(client, listener, make_song):
    song = await make_song()
    await follow(client, listener, song.artist_id)
    r = await client.get("/api/follows/ids", headers=listener.headers)
    assert r.json() == [str(song.artist_id)]
