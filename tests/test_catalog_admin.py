import uuid

import pytest

from app.config import get_settings
from tests.audio_fixtures import insert_song, make_wav
from tests.helpers import make_admin_client, signup

FIELDS = {"title": "Nueva", "artist": "Artista", "album": "Disco"}


def _files(media_dir):
    return sorted(p.name for p in media_dir.iterdir())


@pytest.fixture
async def admin(session, client):
    c = await make_admin_client(session, client)
    yield c
    await c.aclose()


@pytest.fixture
def small_upload_limit(monkeypatch):
    monkeypatch.setenv("FLDSMDFR_MAX_UPLOAD_BYTES", "1024")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


async def test_listener_cannot_upload(client, tmp_path):
    await signup(client)
    wav = make_wav(tmp_path / "a.wav", 1)
    r = await client.post(
        "/api/songs", data=FIELDS, files={"file": ("a.wav", wav.read_bytes(), "audio/wav")}
    )
    assert r.status_code == 403


async def test_admin_uploads_wav(admin, tmp_path):
    wav = make_wav(tmp_path / "a.wav", 3)
    r = await admin.post(
        "/api/songs", data=FIELDS, files={"file": ("a.wav", wav.read_bytes(), "audio/wav")}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["duration_seconds"] == 3
    assert body["title"] == "Nueva"
    listing = (await admin.get("/api/songs")).json()
    assert [s["id"] for s in listing["items"]] == [body["id"]]
    assert (await admin.get(f"/api/songs/{body['id']}/stream")).status_code == 200


async def test_upload_garbage_mp3_rejected_without_orphan(admin, media_dir):
    before = _files(media_dir)
    r = await admin.post(
        "/api/songs", data=FIELDS, files={"file": ("x.mp3", b"no soy audio" * 100, "audio/mpeg")}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_audio"
    assert _files(media_dir) == before


async def test_upload_unsupported_extension(admin, media_dir):
    before = _files(media_dir)
    r = await admin.post(
        "/api/songs", data=FIELDS, files={"file": ("x.flac", b"fLaC" * 10, "audio/flac")}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unsupported_format"
    assert _files(media_dir) == before


async def test_upload_too_large(admin, media_dir, small_upload_limit):
    before = _files(media_dir)
    r = await admin.post(
        "/api/songs", data=FIELDS, files={"file": ("x.wav", b"\0" * 2048, "audio/wav")}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "file_too_large"
    assert _files(media_dir) == before


async def test_upload_missing_title(admin, tmp_path):
    wav = make_wav(tmp_path / "a.wav", 1)
    r = await admin.post(
        "/api/songs",
        data={"artist": "A", "album": "B"},
        files={"file": ("a.wav", wav.read_bytes(), "audio/wav")},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_input"


async def test_admin_updates_title(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    r = await admin.patch(f"/api/songs/{song.id}", json={"title": "Otro título"})
    assert r.status_code == 200
    assert r.json()["title"] == "Otro título"
    assert r.json()["artist"] == song.artist


async def test_update_rejects_empty_title_and_unknown_song(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    assert (await admin.patch(f"/api/songs/{song.id}", json={"title": ""})).status_code == 422
    r = await admin.patch(f"/api/songs/{uuid.uuid4()}", json={"title": "x"})
    assert r.status_code == 404


async def test_listener_cannot_update_or_deactivate(client, session, media_dir):
    song = await insert_song(session, media_dir)
    await signup(client)
    assert (await client.patch(f"/api/songs/{song.id}", json={"title": "x"})).status_code == 403
    assert (await client.delete(f"/api/songs/{song.id}")).status_code == 403


async def test_admin_deactivates_song(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    assert (await admin.delete(f"/api/songs/{song.id}")).status_code == 204
    assert (await admin.get(f"/api/songs/{song.id}")).status_code == 404
    assert (await admin.get("/api/songs")).json()["total"] == 0
    assert (await admin.delete(f"/api/songs/{uuid.uuid4()}")).status_code == 404


async def test_import_song_file_validates_and_copies(session, media_dir, tmp_path):
    from app.modules.catalog import service
    from app.shared.errors import InvalidInput

    wav = make_wav(tmp_path / "seed.wav", 2)
    song = await service.import_song_file(session, wav, "Semilla", "Seed", "Uno")
    assert song.duration_seconds == 2
    assert wav.exists()
    bad = tmp_path / "bad.mp3"
    bad.write_bytes(b"nada" * 50)
    before = _files(media_dir)
    with pytest.raises(InvalidInput) as exc:
        await service.import_song_file(session, bad, "X", "Y", "Z")
    assert exc.value.code == "invalid_audio"
    assert _files(media_dir) == before


async def test_stream_rejects_path_outside_media_dir(client, session, media_dir):
    from app.modules.catalog import repository
    from app.modules.catalog.models import Song

    outside = media_dir.parent / "outside.wav"
    make_wav(outside, 1)
    try:
        song = Song(
            title="Fuga",
            artist="A",
            album="B",
            duration_seconds=1,
            file_path="../outside.wav",
            mime_type="audio/wav",
            size_bytes=outside.stat().st_size,
        )
        await repository.add(session, song)
        await signup(client)
        r = await client.get(f"/api/songs/{song.id}/stream")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "audio_missing"
    finally:
        outside.unlink(missing_ok=True)
