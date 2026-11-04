import pytest

from tests.audio_fixtures import insert_song, set_cover
from tests.helpers import signup

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture
async def user(client):
    await signup(client)
    return client


async def test_follow_case_insensitive(user, session, media_dir):
    await insert_song(session, media_dir, artist="Natalia Lafourcade")
    assert (await user.put("/api/me/follows/natalia LAFOURCADE ")).status_code == 204
    follows = (await user.get("/api/me/follows")).json()
    assert [f["artist"] for f in follows] == ["Natalia Lafourcade"]
    assert (await user.put("/api/me/follows/Natalia Lafourcade")).status_code == 204
    assert len((await user.get("/api/me/follows")).json()) == 1


async def test_follow_artist_with_slash(user, session, media_dir):
    await insert_song(session, media_dir, artist="Calle 13/Residente")
    assert (await user.put("/api/me/follows/Calle%2013%2FResidente")).status_code == 204
    assert (await user.get("/api/me/follows")).json()[0]["artist"] == "Calle 13/Residente"


async def test_follow_unknown_artist_404(user):
    r = await user.put("/api/me/follows/Nadie")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "artist_not_found"


async def test_unfollow_idempotent(user, session, media_dir):
    await insert_song(session, media_dir, artist="Masego")
    await user.put("/api/me/follows/Masego")
    assert (await user.delete("/api/me/follows/masego")).status_code == 204
    assert (await user.delete("/api/me/follows/masego")).status_code == 204
    assert (await user.get("/api/me/follows")).json() == []


async def test_follow_list_has_counts_and_cover(user, client, session, media_dir):
    await insert_song(session, media_dir, title="Vieja", artist="Masego")
    nueva = await insert_song(session, media_dir, title="Nueva", artist="Masego")
    await set_cover(nueva.id)
    await user.put("/api/me/follows/Masego")
    f = (await user.get("/api/me/follows")).json()[0]
    assert f["song_count"] == 2
    assert f["cover_song_id"] == str(nueva.id)
