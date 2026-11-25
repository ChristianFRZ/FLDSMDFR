from sqlalchemy import text

from meloxo_common.db import get_engine


async def _playlist_with(client, user, songs):
    playlist = (await client.post("/api/playlists", json={"name": "Mía"}, headers=user.headers)).json()
    for song in songs:
        r = await client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=user.headers)
        assert r.status_code == 201, r.text
    return playlist


async def test_playlist_with_250_songs_lists_all_songs(client, listener, fake_catalog):
    songs = [fake_catalog.add_song(title=f"Pista {i}") for i in range(250)]
    playlist = (await client.post("/api/playlists", json={"name": "Larga"}, headers=listener.headers)).json()
    async with get_engine().begin() as conn:
        for position, song in enumerate(songs, start=1):
            await conn.execute(
                text("INSERT INTO playlist_songs (playlist_id, song_id, position, metadata_cache) VALUES (:p, :s, :n, '{}')"),
                {"p": playlist["id"], "s": song.id, "n": position},
            )
    fake_catalog.calls.clear()
    body = (await client.get(f"/api/playlists/{playlist['id']}", headers=listener.headers)).json()
    assert len(body["songs"]) == 250
    assert body["degraded"] is False
    assert all(item["available"] and item["title"].startswith("Pista") for item in body["songs"])
    assert len(fake_catalog.calls) == 2


async def test_playlist_degraded_when_catalog_down(client, listener, fake_catalog):
    playlist = await _playlist_with(client, listener, [fake_catalog.add_song(title="Guardada")])
    fake_catalog.down = True
    r = await client.get(f"/api/playlists/{playlist['id']}", headers=listener.headers)
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    assert body["songs"][0]["title"] == "Guardada"
    assert body["songs"][0]["available"] is True  # sin catálogo se confía en la caché


async def test_playlist_song_missing_from_catalog_is_unavailable(client, listener, fake_catalog):
    song = fake_catalog.add_song(title="Se fue")
    playlist = await _playlist_with(client, listener, [song])
    fake_catalog.delete(song)
    body = (await client.get(f"/api/playlists/{playlist['id']}", headers=listener.headers)).json()
    assert body["degraded"] is False
    assert body["songs"][0]["available"] is False


async def test_missing_song_in_tape_is_shown_unavailable(client, listener, fake_catalog):
    song = fake_catalog.add_song(title="Se fue")
    tape = (await client.post("/api/tapes", json={"title": "Viaje", "color": "pink"}, headers=listener.headers)).json()
    r = await client.post(f"/api/tapes/{tape['id']}/tracks", json={"song_id": str(song.id)}, headers=listener.headers)
    assert r.status_code == 201, r.text
    fake_catalog.delete(song)
    r = await client.get(f"/api/tapes/{tape['id']}", headers=listener.headers)
    assert r.status_code == 200
    track = r.json()["tracks"][0]
    assert track["song"]["title"] == "Se fue"
    assert track["song"]["available"] is False


async def test_missing_song_in_favorites_renders_placeholder(client, listener, fake_catalog):
    song = fake_catalog.add_song()
    await client.put(f"/api/favorites/{song.id}", headers=listener.headers)
    fake_catalog.delete(song)
    r = await client.get("/api/favorites", headers=listener.headers)
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["available"] is False
    assert item["title"] == "Pista eliminada"
