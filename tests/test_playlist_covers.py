import pytest
from httpx import AsyncClient

from tests.helpers import signup

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
async def owner(client):
    await signup(client)
    return client


@pytest.fixture
async def other(client):
    c = AsyncClient(transport=client._transport, base_url="http://test")
    await signup(c, email="otra@test.mx", name="Otra")
    yield c
    await c.aclose()


async def _playlist(c) -> dict:
    r = await c.post("/api/playlists", json={"name": "Con portada"})
    assert r.status_code == 201, r.text
    return r.json()


async def _put(c, pid, content=PNG):
    return await c.put(
        f"/api/playlists/{pid}/cover", files={"file": ("c.png", content, "image/png")}
    )


async def test_owner_uploads_cover(owner):
    pl = await _playlist(owner)
    assert pl["has_cover"] is False
    r = await _put(owner, pl["id"])
    assert r.status_code == 200, r.text
    assert r.json()["has_cover"] is True
    assert (await owner.get("/api/playlists")).json()[0]["has_cover"] is True
    assert (await owner.get(f"/api/playlists/{pl['id']}")).json()["has_cover"] is True
    g = await owner.get(f"/api/playlists/{pl['id']}/cover")
    assert g.status_code == 200
    assert g.content == PNG


async def test_other_user_cover_404(owner, other):
    pl = await _playlist(owner)
    await _put(owner, pl["id"])
    r = await _put(other, pl["id"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "playlist_not_found"
    g = await other.get(f"/api/playlists/{pl['id']}/cover")
    assert g.status_code == 404
    assert g.json()["error"]["code"] == "playlist_not_found"


async def test_delete_playlist_removes_cover_file(owner, media_dir):
    pl = await _playlist(owner)
    await _put(owner, pl["id"])
    covers = media_dir / "covers" / "playlists"
    assert list(covers.glob(f"{pl['id']}.*"))
    assert (await owner.delete(f"/api/playlists/{pl['id']}")).status_code == 204
    assert not list(covers.glob(f"{pl['id']}.*"))
