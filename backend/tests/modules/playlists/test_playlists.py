import pytest

from app.modules.playlists import public, service


async def create(client, user, name="Viaje", **kw):
    r = await client.post("/api/playlists", json={"name": name, **kw}, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


async def add(client, user, playlist, song):
    return await client.post(
        f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=user.headers
    )


async def read(client, user, playlist):
    return await client.get(f"/api/playlists/{playlist['id']}", headers=user.headers)


async def test_owner_from_token_not_body(client, listener, make_user):
    other = await make_user()
    r = await client.post("/api/playlists", json={"name": "x", "owner_id": other.id}, headers=listener.headers)
    assert r.json()["owner_id"] == listener.id


async def test_add_song_idempotent(client, listener, make_song):
    song, playlist = await make_song(), await create(client, listener)
    assert (await add(client, listener, playlist, song)).status_code == 201
    assert (await add(client, listener, playlist, song)).status_code == 200
    assert len((await read(client, listener, playlist)).json()["songs"]) == 1


async def test_add_unknown_song_404(client, listener):
    playlist = await create(client, listener)
    r = await client.post(
        f"/api/playlists/{playlist['id']}/songs",
        json={"song_id": "00000000-0000-0000-0000-000000000000"},
        headers=listener.headers,
    )
    assert r.status_code == 404


async def test_foreign_private_403(client, listener, make_user):
    other, playlist = await make_user(), await create(client, listener)
    assert (await read(client, other, playlist)).status_code == 403


async def test_foreign_public_readable_not_editable(client, listener, make_user, make_song):
    other, song = await make_user(), await make_song()
    playlist = await create(client, listener, is_public=True)
    assert (await read(client, other, playlist)).status_code == 200
    assert (await add(client, other, playlist, song)).status_code == 403


async def test_foreign_cannot_edit_or_delete(client, listener, make_user):
    other, playlist = await make_user(), await create(client, listener)
    url = f"/api/playlists/{playlist['id']}"
    assert (await client.patch(url, json={"name": "x"}, headers=other.headers)).status_code == 403
    assert (await client.delete(url, headers=other.headers)).status_code == 403


async def test_edit_and_delete(client, listener):
    playlist = await create(client, listener)
    url = f"/api/playlists/{playlist['id']}"
    r = await client.patch(url, json={"name": "Nuevo"}, headers=listener.headers)
    assert r.json()["name"] == "Nuevo"
    assert (await client.delete(url, headers=listener.headers)).status_code == 204
    assert (await client.get(url, headers=listener.headers)).status_code == 404


async def test_list_only_mine(client, listener, make_user):
    other = await make_user()
    await create(client, listener)
    await create(client, other, name="Ajena")
    r = await client.get("/api/playlists", headers=listener.headers)
    assert [p["name"] for p in r.json()] == ["Viaje"]


async def test_remove_song(client, listener, make_song):
    song, playlist = await make_song(), await create(client, listener)
    await add(client, listener, playlist, song)
    r = await client.delete(f"/api/playlists/{playlist['id']}/songs/{song.id}", headers=listener.headers)
    assert r.status_code == 204
    assert (await read(client, listener, playlist)).json()["songs"] == []


async def test_order_keeps_insertion(client, listener, make_song):
    a, b = await make_song(title="A"), await make_song(title="B")
    playlist = await create(client, listener)
    await add(client, listener, playlist, b)
    await add(client, listener, playlist, a)
    titles = [s["title"] for s in (await read(client, listener, playlist)).json()["songs"]]
    assert titles == ["B", "A"]


async def test_not_degraded_normally(client, listener, make_song):
    song, playlist = await make_song(), await create(client, listener)
    await add(client, listener, playlist, song)
    assert (await read(client, listener, playlist)).json()["degraded"] is False


async def test_degraded_when_catalog_fails(client, listener, make_song, monkeypatch):
    song, playlist = await make_song(), await create(client, listener)
    await add(client, listener, playlist, song)

    async def broken(_):
        raise RuntimeError("catálogo caído")

    monkeypatch.setattr(service, "get_songs", broken)
    r = await read(client, listener, playlist)
    assert r.status_code == 200
    assert r.json()["degraded"] is True
    assert r.json()["songs"][0]["title"] == "Luz de carretera"


async def test_add_while_catalog_down_503(client, listener, make_song, monkeypatch):
    song, playlist = await make_song(), await create(client, listener)

    async def broken(_):
        raise RuntimeError("catálogo caído")

    monkeypatch.setattr(service, "get_songs", broken)
    assert (await add(client, listener, playlist, song)).status_code == 503


async def test_unavailable_song_marked_not_dropped(client, admin, listener, make_song):
    song, playlist = await make_song(), await create(client, listener)
    await add(client, listener, playlist, song)
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    item = (await read(client, listener, playlist)).json()["songs"][0]
    assert item["available"] is False
    assert item["title"] == "Luz de carretera"


async def test_deleted_song_stays_as_unavailable(client, listener, composer):
    from tests.media import mp3

    r = await client.post(
        "/api/composer/tracks",
        data={"title": "Se va", "genre": "rock", "license": "CC"},
        files={"audio": ("a.mp3", mp3())},
        headers=composer.headers,
    )
    song_id = r.json()["id"]
    await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    playlist = await create(client, listener)
    await client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": song_id}, headers=listener.headers)
    await client.delete(f"/api/composer/tracks/{song_id}", headers=composer.headers)
    item = (await read(client, listener, playlist)).json()["songs"][0]
    assert item["available"] is False
    assert item["title"] == "Se va"


@pytest.mark.parametrize("copies", [1, 2])
async def test_count_inclusions(client, listener, make_song, copies):
    song = await make_song()
    for i in range(copies):
        await add(client, listener, await create(client, listener, name=f"P{i}"), song)
    assert await public.count_inclusions([song.id]) == copies
