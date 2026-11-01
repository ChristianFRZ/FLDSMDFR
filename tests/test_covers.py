import pytest

from tests.audio_fixtures import insert_song, make_wav
from tests.helpers import make_admin_client, signup

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
JPEG_HEAD = b"\xff\xd8\xff"
WEBP = b"RIFF" + b"\0" * 4 + b"WEBP" + b"1" * 50
MAX = 2_097_152


@pytest.fixture
async def admin(session, client):
    c = await make_admin_client(session, client)
    yield c
    await c.aclose()


async def _put(c, song_id, content, name="cover.png"):
    return await c.put(f"/api/songs/{song_id}/cover", files={"file": (name, content, "image/png")})


async def test_admin_uploads_png_cover(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    r = await _put(admin, song.id, PNG)
    assert r.status_code == 200, r.text
    assert r.json()["has_cover"] is True
    g = await admin.get(f"/api/songs/{song.id}/cover")
    assert g.status_code == 200
    assert g.headers["content-type"] == "image/png"
    assert g.content == PNG


async def test_cover_etag_304(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    await _put(admin, song.id, PNG)
    first = await admin.get(f"/api/songs/{song.id}/cover")
    etag = first.headers["etag"]
    second = await admin.get(f"/api/songs/{song.id}/cover", headers={"If-None-Match": etag})
    assert second.status_code == 304


async def test_listener_cannot_upload_cover(client, session, media_dir):
    await signup(client)
    song = await insert_song(session, media_dir)
    r = await _put(client, song.id, PNG)
    assert r.status_code == 403


async def test_fake_png_rejected_keeps_previous(admin, session, media_dir, tmp_path):
    song = await insert_song(session, media_dir)
    await _put(admin, song.id, PNG)
    fake = make_wav(tmp_path / "x.wav", 0.1).read_bytes()
    r = await _put(admin, song.id, fake, name="x.png")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_image"
    g = await admin.get(f"/api/songs/{song.id}/cover")
    assert g.content == PNG


async def test_oversized_cover_413(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    r = await _put(admin, song.id, JPEG_HEAD + b"0" * (MAX + 1 - len(JPEG_HEAD)), name="a.jpg")
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "image_too_large"


async def test_replace_with_other_format_removes_old(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    await _put(admin, song.id, PNG)
    r = await _put(admin, song.id, WEBP, name="a.webp")
    assert r.status_code == 200
    files = sorted(p.name for p in (media_dir / "covers" / "songs").glob(f"{song.id}.*"))
    assert files == [f"{song.id}.webp"]


async def test_cover_404_when_missing(admin, session, media_dir):
    song = await insert_song(session, media_dir)
    r = await admin.get(f"/api/songs/{song.id}/cover")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "cover_not_found"
