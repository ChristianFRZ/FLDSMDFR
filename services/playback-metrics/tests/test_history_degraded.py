"""Historial con copias: si el catálogo no responde se muestran las copias del último evento."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from tests.audio_fixtures import insert_song
from tests.fake_catalog import FakeCatalog
from tests.helpers import signup

T0 = datetime(2026, 10, 1, 12, tzinfo=UTC)


@pytest.fixture
async def user(client):
    client.user_id = uuid.UUID((await signup(client))["user"]["id"])
    return client


async def _play(c, song_id, minutes=0):
    r = await c.post(
        "/api/playbacks",
        json={
            "playback_id": str(uuid.uuid4()),
            "song_id": str(song_id),
            "listened_seconds": 30,
            "occurred_at": (T0 + timedelta(minutes=minutes)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text


async def test_playback_stores_snapshot(user, session, media_dir):
    song = await insert_song(session, media_dir, title="Lluvia", artist="Nube", album="Cielo")
    await _play(user, song.id)
    row = (
        await session.execute(
            text(
                "SELECT title_snapshot, artist_snapshot, album_snapshot, duration_snapshot "
                "FROM playback_events WHERE song_id = :id"
            ),
            {"id": song.id},
        )
    ).one()
    assert tuple(row) == ("Lluvia", "Nube", "Cielo", song.duration_seconds)


async def test_history_degraded_nested_song_defaults(user, session, media_dir, take_down):
    song = await insert_song(session, media_dir, title="Lluvia", artist="Nube", album="Cielo")
    await _play(user, song.id)
    take_down("catalog-streaming")
    r = await user.get("/api/me/history")
    assert r.status_code == 200
    page = r.json()
    assert page["degraded"] is True
    assert page["total"] == 1
    [item] = page["items"]
    assert item["status"] == "degraded"
    assert item["available"] is False
    nested = item["song"]
    assert (nested["id"], nested["title"], nested["artist"], nested["album"]) == (
        str(song.id),
        "Lluvia",
        "Nube",
        "Cielo",
    )
    assert nested["duration_seconds"] == song.duration_seconds
    assert nested["is_active"] is False
    assert nested["has_cover"] is False
    assert nested["created_at"] == item["last_played_at"]
    assert nested["size_bytes"] == 0
    assert nested["mime_type"] == ""


async def test_history_ok_status(user, session, media_dir):
    await _play(user, (await insert_song(session, media_dir)).id)
    page = (await user.get("/api/me/history")).json()
    assert page["degraded"] is False
    assert page["items"][0]["status"] == "ok"
    assert page["items"][0]["available"] is True


async def test_history_unavailable_status(user, session, media_dir):
    song = await insert_song(session, media_dir)
    await _play(user, song.id)
    FakeCatalog.current.deactivate(song.id)
    item = (await user.get("/api/me/history")).json()["items"][0]
    assert (item["status"], item["available"]) == ("unavailable", False)


async def test_history_old_event_without_snapshot(user, session, take_down):
    await session.execute(
        text(
            "INSERT INTO playback_events "
            "(playback_id, song_id, user_id, listened_seconds, occurred_at) "
            "VALUES (:p, :s, :u, 30, :t)"
        ),
        {"p": uuid.uuid4(), "s": uuid.uuid4(), "u": user.user_id, "t": T0},
    )
    await session.commit()
    take_down("catalog-streaming")
    [item] = (await user.get("/api/me/history")).json()["items"]
    song = item["song"]
    assert (song["title"], song["artist"], song["duration_seconds"]) == (
        "Canción no disponible",
        "",
        0,
    )


async def test_history_omits_missing_when_catalog_up(user, session, media_dir):
    song = await insert_song(session, media_dir)
    await _play(user, song.id)
    del FakeCatalog.current.songs[song.id]
    assert (await user.get("/api/me/history")).json()["items"] == []


async def test_read_refreshes_snapshot(user, session, media_dir):
    song = await insert_song(session, media_dir, title="Viejo")
    await _play(user, song.id)
    fake = FakeCatalog.current
    fake.songs[song.id] = fake.songs[song.id].model_copy(update={"title": "Nuevo"})
    assert (await user.get("/api/me/history")).json()["items"][0]["song"]["title"] == "Nuevo"
    title = (
        await session.execute(
            text("SELECT title_snapshot FROM playback_events WHERE song_id = :id"),
            {"id": song.id},
        )
    ).scalar_one()
    assert title == "Nuevo"


async def test_snapshot_write_failure_still_200(user, session, media_dir, monkeypatch):
    song = await insert_song(session, media_dir, title="Viejo")
    await _play(user, song.id)
    fake = FakeCatalog.current
    fake.songs[song.id] = fake.songs[song.id].model_copy(update={"title": "Nuevo"})

    async def boom(*args, **kwargs):
        raise RuntimeError("la base no acepta la escritura")

    monkeypatch.setattr("app.modules.playback.repository.save_snapshots", boom)
    r = await user.get("/api/me/history")
    assert r.status_code == 200
    assert r.json()["items"][0]["song"]["title"] == "Nuevo"
