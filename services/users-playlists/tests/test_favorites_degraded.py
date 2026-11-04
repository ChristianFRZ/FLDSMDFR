"""Favoritas con copias: si el catálogo no responde se muestran las últimas copias guardadas."""

import uuid

import pytest
from sqlalchemy import text

from tests.audio_fixtures import insert_song
from tests.fake_catalog import FakeCatalog
from tests.helpers import signup


@pytest.fixture
async def user(client):
    await signup(client)
    return client


async def _like(user, song) -> None:
    assert (await user.put(f"/api/me/favorites/{song.id}")).status_code == 204


async def test_like_stores_snapshot(user, session, media_dir):
    song = await insert_song(
        session, media_dir, title="Lluvia", artist="Nube", album="Cielo", seconds=7
    )
    await _like(user, song)
    row = (
        await session.execute(
            text(
                "SELECT title_snapshot, artist_snapshot, album_snapshot, duration_snapshot "
                "FROM favorites WHERE song_id = :id"
            ),
            {"id": song.id},
        )
    ).one()
    assert tuple(row) == ("Lluvia", "Nube", "Cielo", 7)


async def test_favorites_degraded_uses_snapshot(user, session, media_dir, catalog_down_later):
    song = await insert_song(session, media_dir, title="Lluvia", artist="Nube", seconds=7)
    await _like(user, song)
    catalog_down_later()
    r = await user.get("/api/me/favorites")
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is True
    [fav] = body["songs"]
    assert (fav["title"], fav["artist"], fav["status"]) == ("Lluvia", "Nube", "degraded")
    assert fav["duration_seconds"] == 7
    assert fav["has_cover"] is False


async def test_favorites_ok_not_degraded(user, session, media_dir):
    await _like(user, await insert_song(session, media_dir))
    body = (await user.get("/api/me/favorites")).json()
    assert body["degraded"] is False
    assert body["songs"][0]["status"] == "ok"


async def test_old_row_without_snapshot(user, session, catalog_down):
    me = (await user.get("/api/auth/me")).json()["id"]
    await session.execute(
        text("INSERT INTO favorites (user_id, song_id) VALUES (:u, :s)"),
        {"u": uuid.UUID(me), "s": uuid.uuid4()},
    )
    await session.commit()
    [fav] = (await user.get("/api/me/favorites")).json()["songs"]
    assert (fav["title"], fav["artist"], fav["duration_seconds"]) == (
        "Canción no disponible",
        "",
        0,
    )
    assert fav["status"] == "degraded"


async def test_read_refreshes_snapshot(user, session, media_dir):
    song = await insert_song(session, media_dir, title="Viejo")
    await _like(user, song)
    fake = FakeCatalog.current
    fake.songs[song.id] = fake.songs[song.id].model_copy(update={"title": "Nuevo"})
    assert (await user.get("/api/me/favorites")).json()["songs"][0]["title"] == "Nuevo"
    title = (
        await session.execute(
            text("SELECT title_snapshot FROM favorites WHERE song_id = :id"), {"id": song.id}
        )
    ).scalar_one()
    assert title == "Nuevo"


async def test_snapshot_write_failure_still_200(user, session, media_dir, monkeypatch):
    song = await insert_song(session, media_dir, title="Viejo")
    await _like(user, song)
    fake = FakeCatalog.current
    fake.songs[song.id] = fake.songs[song.id].model_copy(update={"title": "Nuevo"})

    async def boom(*args, **kwargs):
        raise RuntimeError("la base no acepta la escritura")

    monkeypatch.setattr("app.modules.social.repository.save_snapshots", boom)
    r = await user.get("/api/me/favorites")
    assert r.status_code == 200
    assert r.json()["songs"][0]["title"] == "Nuevo"


async def test_total_seconds_includes_degraded(user, session, media_dir, catalog_down_later):
    await _like(user, await insert_song(session, media_dir, title="A", seconds=3))
    await _like(user, await insert_song(session, media_dir, title="B", seconds=4))
    catalog_down_later()
    assert (await user.get("/api/me/favorites")).json()["total_seconds"] == 7
