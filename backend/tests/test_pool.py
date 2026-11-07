"""Con carga, una petición no debe retener su conexión mientras otro módulo abre la suya."""
from app.core.db import get_engine
from app.modules.playback import service as playback
from app.modules.playlists import service as playlists
from app.modules.social import service as social


def spy(module, name, monkeypatch):
    original = getattr(module, name)
    seen = []

    async def wrapper(*args):
        seen.append(get_engine().pool.checkedout())
        return await original(*args)

    monkeypatch.setattr(module, name, wrapper)
    return seen


async def test_playlist_detail_releases_connection(client, listener, make_song, monkeypatch):
    song = await make_song()
    playlist = (await client.post("/api/playlists", json={"name": "x"}, headers=listener.headers)).json()
    url = f"/api/playlists/{playlist['id']}"
    await client.post(f"{url}/songs", json={"song_id": str(song.id)}, headers=listener.headers)
    seen = spy(playlists, "get_songs", monkeypatch)
    await client.get(url, headers=listener.headers)
    assert seen == [0]


async def test_history_releases_connection(client, listener, monkeypatch):
    seen = spy(playback, "get_songs", monkeypatch)
    await client.get("/api/playbacks/history", headers=listener.headers)
    assert seen == [0]


async def test_favorites_releases_connection(client, listener, monkeypatch):
    seen = spy(social, "get_songs", monkeypatch)
    await client.get("/api/favorites", headers=listener.headers)
    assert seen == [0]


async def test_notices_releases_connection(client, listener, make_song, monkeypatch):
    song = await make_song()
    await client.put(f"/api/follows/{song.artist_id}", headers=listener.headers)
    seen = spy(social, "published_since", monkeypatch)
    await client.get("/api/notices", headers=listener.headers)
    assert seen == [0]


async def test_releases_releases_connection(client, listener, make_song, monkeypatch):
    song = await make_song()
    await client.put(f"/api/follows/{song.artist_id}", headers=listener.headers)
    seen = spy(social, "upcoming_for_artists", monkeypatch)
    await client.get("/api/releases", headers=listener.headers)
    assert seen == [0]


async def test_follows_releases_connection(client, listener, make_song, monkeypatch):
    song = await make_song()
    await client.put(f"/api/follows/{song.artist_id}", headers=listener.headers)
    seen = spy(social, "get_artists", monkeypatch)
    await client.get("/api/follows", headers=listener.headers)
    assert seen == [0]
