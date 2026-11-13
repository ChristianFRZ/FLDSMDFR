import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from meloxo_common import db
from meloxo_common.config import get_base_settings


async def _playlist(client, user, name="Mía"):
    return (await client.post("/api/playlists", json={"name": name}, headers=user.headers)).json()


async def test_add_song_returns_503_when_catalog_down(client, listener, fake_catalog):
    song = fake_catalog.add_song()
    playlist = await _playlist(client, listener)
    fake_catalog.down = True
    r = await client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=listener.headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "catalog_unavailable"


async def test_add_song_unknown_in_catalog_is_404(client, listener, fake_catalog):
    song = fake_catalog.add_song()
    fake_catalog.delete(song)
    playlist = await _playlist(client, listener)
    r = await client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=listener.headers)
    assert r.status_code == 404


async def test_add_song_to_playlist_deleted_during_catalog_call_is_404(client, listener, fake_catalog):
    song = fake_catalog.add_song()
    playlist = await _playlist(client, listener)
    fake_catalog.delay = 0.6

    async def delete_meanwhile():
        await asyncio.sleep(0.2)
        return await client.delete(f"/api/playlists/{playlist['id']}", headers=listener.headers)

    added, deleted = await asyncio.gather(
        client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=listener.headers),
        delete_meanwhile(),
    )
    assert deleted.status_code == 204
    assert added.status_code == 404
    assert added.json()["error"]["code"] == "playlist_not_found"


@pytest.fixture
async def one_connection_pool(monkeypatch):
    """Un pool de una sola conexión y 0,4 s de espera: retener la conexión durante una llamada lenta lo agota."""
    engine = create_async_engine(get_base_settings().DATABASE_URL, pool_size=1, max_overflow=0, pool_timeout=0.4)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "_sessionmaker", lambda: maker)
    yield
    await engine.dispose()


async def test_add_song_does_not_hold_connection_during_catalog_call(
    client, listener, fake_catalog, one_connection_pool
):
    songs = [fake_catalog.add_song(title=f"Pista {i}") for i in range(2)]
    first, second = await _playlist(client, listener, "A"), await _playlist(client, listener, "B")
    fake_catalog.delay = 1.0
    results = await asyncio.gather(
        *(
            client.post(f"/api/playlists/{p['id']}/songs", json={"song_id": str(s.id)}, headers=listener.headers)
            for p, s in ((first, songs[0]), (second, songs[1]))
        )
    )
    assert [r.status_code for r in results] == [201, 201]
