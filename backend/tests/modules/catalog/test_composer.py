from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import session_scope
from app.modules.catalog.models import Song
from tests.media import JPG, PNG, mp3


def media_files():
    return {p for p in Path(get_settings().MEDIA_DIR).rglob("*") if p.is_file()}


def form(**kw):
    return {"title": "Mi pista", "genre": "rock", "license": "CC BY 4.0", **kw}


async def upload(client, user, audio=None, cover=None, name="pista.mp3", **fields):
    files = {"audio": (name, audio if audio is not None else mp3(), "audio/mpeg")}
    if cover is not None:
        files["cover"] = ("c.jpg", cover, "image/jpeg")
    return await client.post("/api/composer/tracks", data=form(**fields), files=files, headers=user.headers)


async def test_upload_ok_is_draft(client, composer):
    r = await upload(client, composer, cover=JPG)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft"
    assert body["source"] == "local"
    assert body["duration"] > 0
    async with session_scope() as session:
        song = (await session.execute(select(Song))).unique().scalar_one()
    assert song.audio_path == f"audio/{Path(song.audio_path).stem}.mp3"
    assert "pista" not in song.audio_path


async def test_png_cover_accepted(client, composer):
    assert (await upload(client, composer, cover=PNG)).status_code == 201


async def test_upload_creates_artist_with_display_name(client, composer):
    body = (await upload(client, composer)).json()
    assert body["artist"] == composer.email.split("@")[0]


async def test_upload_with_future_publish_at_is_scheduled(client, composer):
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    body = (await upload(client, composer, publish_at=when)).json()
    assert body["status"] == "scheduled"


async def test_past_publish_at_rejected(client, composer):
    when = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    r = await upload(client, composer, publish_at=when)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "publish_at_past"


async def test_text_disguised_as_mp3_rejected(client, composer):
    before = media_files()
    r = await upload(client, composer, audio=b"esto es texto " * 100)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_audio"
    assert media_files() == before


async def test_id3_prefix_without_audio_rejected(client, composer):
    assert (await upload(client, composer, audio=b"ID3" + b"\x00" * 500)).status_code == 422


async def test_cover_not_image_rejected(client, composer):
    before = media_files()
    r = await upload(client, composer, cover=b"<svg></svg>" * 20)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_cover"
    assert media_files() == before


async def test_mp3_over_limit_rejected(client, composer, monkeypatch):
    monkeypatch.setattr(get_settings(), "UPLOAD_MAX_MP3_MB", 1)
    before = media_files()
    r = await upload(client, composer, audio=mp3(3000))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "audio_too_large"
    assert media_files() == before


async def test_cover_over_2mb_rejected(client, composer):
    r = await upload(client, composer, cover=JPG + b"\x00" * (2 * 1024 * 1024 + 1))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "cover_too_large"


async def test_duration_over_limit_rejected(client, composer, monkeypatch):
    monkeypatch.setattr(get_settings(), "UPLOAD_MAX_MINUTES", 0)
    r = await upload(client, composer)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "audio_too_long"


@pytest.mark.parametrize("name", ["../../x.mp3", "..\\..\\x.mp3", "/etc/passwd"])
async def test_filename_traversal_ignored(client, composer, name):
    assert (await upload(client, composer, name=name)).status_code == 201
    root = Path(get_settings().MEDIA_DIR).resolve()
    assert all(p.resolve().is_relative_to(root) for p in media_files())


@pytest.mark.parametrize("missing", ["title", "genre", "license"])
async def test_required_fields(client, composer, missing):
    data = form()
    data.pop(missing)
    r = await client.post(
        "/api/composer/tracks", data=data, files={"audio": ("a.mp3", mp3())}, headers=composer.headers
    )
    assert r.status_code == 422


async def test_quota_20_tracks(client, composer, monkeypatch):
    monkeypatch.setattr(get_settings(), "COMPOSER_MAX_TRACKS", 2)
    await upload(client, composer)
    await upload(client, composer)
    r = await upload(client, composer)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "quota_exceeded"


async def test_listener_cannot_upload(client, listener):
    assert (await upload(client, listener)).status_code == 403


async def test_admin_can_upload(client, admin):
    assert (await upload(client, admin)).status_code == 201


async def test_list_own_tracks_any_status(client, composer, make_user):
    other = await make_user(role="composer")
    await upload(client, composer)
    await upload(client, other, title="Ajena")
    items = (await client.get("/api/composer/tracks", headers=composer.headers)).json()
    assert [i["title"] for i in items] == ["Mi pista"]


async def test_edit_own_track(client, composer):
    song = (await upload(client, composer)).json()
    r = await client.patch(f"/api/composer/tracks/{song['id']}", json={"title": "Nuevo"}, headers=composer.headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Nuevo"


async def test_reschedule_and_unschedule(client, composer):
    song = (await upload(client, composer)).json()
    when = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    url = f"/api/composer/tracks/{song['id']}"
    assert (await client.patch(url, json={"publish_at": when}, headers=composer.headers)).json()["status"] == "scheduled"
    assert (await client.patch(url, json={"publish_at": None}, headers=composer.headers)).json()["status"] == "draft"


async def test_cannot_edit_others_track(client, composer, make_user):
    other = await make_user(role="composer")
    song = (await upload(client, other)).json()
    url = f"/api/composer/tracks/{song['id']}"
    assert (await client.patch(url, json={"title": "x"}, headers=composer.headers)).status_code == 403
    assert (await client.delete(url, headers=composer.headers)).status_code == 403
    assert (await client.post(f"{url}/hide", headers=composer.headers)).status_code == 403


async def test_cannot_edit_jamendo_track(client, composer, make_song):
    song = await make_song(artist="J", source="jamendo", jamendo_id="1")
    url = f"/api/composer/tracks/{song.id}"
    assert (await client.patch(url, json={"title": "x"}, headers=composer.headers)).status_code == 403


async def test_hide_and_publish_own_track(client, composer, listener):
    song = (await upload(client, composer)).json()
    url = f"/api/composer/tracks/{song['id']}"
    assert (await client.post(f"{url}/publish", headers=composer.headers)).json()["status"] == "published"
    assert (await client.get("/api/songs", headers=listener.headers)).json()["total"] == 1
    assert (await client.post(f"{url}/hide", headers=composer.headers)).json()["status"] == "hidden"
    assert (await client.get("/api/songs", headers=listener.headers)).json()["total"] == 0


async def test_delete_removes_files(client, composer):
    before = media_files()
    song = (await upload(client, composer, cover=JPG)).json()
    r = await client.delete(f"/api/composer/tracks/{song['id']}", headers=composer.headers)
    assert r.status_code == 204
    assert media_files() == before


async def test_profile_roundtrip(client, composer):
    data = {"name": "Luz Norte", "bio": "Canciones", "links": {"web": "https://x.example"}}
    r = await client.put("/api/composer/profile", json=data, headers=composer.headers)
    assert r.status_code == 200
    got = (await client.get("/api/composer/profile", headers=composer.headers)).json()
    assert got["name"] == "Luz Norte"
    assert got["links"] == {"web": "https://x.example"}


async def test_albums_are_own(client, composer, make_user):
    other = await make_user(role="composer")
    r = await client.post(
        "/api/composer/albums", data={"title": "EP", "kind": "ep"}, headers=composer.headers
    )
    assert r.status_code == 201
    album = r.json()
    assert [a["title"] for a in (await client.get("/api/composer/albums", headers=composer.headers)).json()] == ["EP"]
    assert (await client.get("/api/composer/albums", headers=other.headers)).json() == []
    r = await upload(client, other, album_id=album["id"])
    assert r.status_code == 403


async def test_cover_served_publicly(client, composer):
    body = (await upload(client, composer, cover=JPG)).json()
    r = await client.get(body["cover_url"])
    assert r.status_code == 200
    assert r.content == JPG


async def test_media_route_does_not_serve_audio_or_escape(client, composer):
    await upload(client, composer)
    async with session_scope() as session:
        song = (await session.execute(select(Song))).unique().scalar_one()
    assert (await client.get(f"/api/media/{song.audio_path}")).status_code == 404
    assert (await client.get("/api/media/covers/..%2F..%2Fetc%2Fpasswd")).status_code == 404


@pytest.mark.parametrize("field", ["title", "genre", "license"])
async def test_patch_null_field_rejected(client, composer, field):
    song_id = (await upload(client, composer)).json()["id"]
    r = await client.patch(f"/api/composer/tracks/{song_id}", json={field: None}, headers=composer.headers)
    assert r.status_code == 422
    async with session_scope() as session:
        assert await session.scalar(select(Song.genres).where(Song.id == song_id)) == ["rock"]


@pytest.mark.parametrize("link", ["javascript:alert(1)", "data:text/html,x", "ftp://a.example", "sin-esquema"])
async def test_profile_link_must_be_http(client, composer, link):
    body = {"name": "A", "bio": "", "links": {"web": link}}
    r = await client.put("/api/composer/profile", json=body, headers=composer.headers)
    assert r.status_code == 422


async def test_profile_link_http_saved(client, composer):
    body = {"name": "A", "bio": "", "links": {"web": "https://a.example/yo"}}
    r = await client.put("/api/composer/profile", json=body, headers=composer.headers)
    assert r.status_code == 200
    assert r.json()["links"] == {"web": "https://a.example/yo"}


async def test_track_list_includes_album(client, composer):
    album = await client.post("/api/composer/albums", data={"title": "Disco"}, headers=composer.headers)
    await upload(client, composer, album_id=album.json()["id"])
    items = (await client.get("/api/composer/tracks", headers=composer.headers)).json()
    assert items[0]["album_id"] == album.json()["id"]
