import uuid

import pytest
from httpx import AsyncClient

from app.modules.playlists import service as playlists_service
from tests.audio_fixtures import insert_song
from tests.helpers import signup

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
async def owner(client):
    await signup(client, email="duena@test.mx", name="Marta Ruiz")
    return client


async def _client(client, email, name):
    c = AsyncClient(transport=client._transport, base_url="http://test")
    body = await signup(c, email=email, name=name)
    return c, uuid.UUID(body["user"]["id"])


@pytest.fixture
async def member(client, session, owner):
    c, uid = await _client(client, "colab@test.mx", "Alex Colab")
    r = await owner.post("/api/playlists", json={"name": "Tardes de verano"})
    pid = r.json()["id"]
    await playlists_service.add_member(session, uuid.UUID(pid), uid)
    c.playlist_id = pid
    c.user_id = uid
    yield c
    await c.aclose()


async def test_member_sees_playlist_in_list_as_collaborator(member, owner):
    listing = (await member.get("/api/playlists")).json()
    assert [(p["id"], p["role"]) for p in listing] == [(member.playlist_id, "collaborator")]
    assert (await owner.get("/api/playlists")).json()[0]["role"] == "owner"


async def test_member_can_add_remove_reorder(member, session, media_dir):
    a = await insert_song(session, media_dir, title="A")
    b = await insert_song(session, media_dir, title="B")
    pid = member.playlist_id
    for s in (a, b):
        r = await member.post(f"/api/playlists/{pid}/songs", json={"song_id": str(s.id)})
        assert r.status_code == 201, r.text
    r = await member.put(f"/api/playlists/{pid}/order", json={"song_ids": [str(b.id), str(a.id)]})
    assert [s["title"] for s in r.json()["songs"]] == ["B", "A"]
    r = await member.delete(f"/api/playlists/{pid}/songs/{a.id}")
    assert r.status_code == 200
    detail = (await member.get(f"/api/playlists/{pid}")).json()
    assert detail["role"] == "collaborator"
    assert [s["title"] for s in detail["songs"]] == ["B"]


async def test_member_cannot_rename_delete_or_upload_cover(member):
    pid = member.playlist_id
    assert (await member.patch(f"/api/playlists/{pid}", json={"name": "X"})).status_code == 404
    assert (await member.delete(f"/api/playlists/{pid}")).status_code == 404
    r = await member.put(f"/api/playlists/{pid}/cover", files={"file": ("c.png", PNG, "image/png")})
    assert r.status_code == 404


async def test_owner_removes_member_then_write_404(member, owner, session, media_dir):
    song = await insert_song(session, media_dir)
    pid = member.playlist_id
    r = await owner.delete(f"/api/playlists/{pid}/members/{member.user_id}")
    assert r.status_code == 204
    r = await member.post(f"/api/playlists/{pid}/songs", json={"song_id": str(song.id)})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "playlist_not_found"
    assert (await member.get("/api/playlists")).json() == []


async def test_member_leaves(member):
    pid = member.playlist_id
    r = await member.delete(f"/api/playlists/{pid}/members/{member.user_id}")
    assert r.status_code == 204
    assert (await member.get("/api/playlists")).json() == []


async def test_member_cannot_remove_other_member(member, client, session):
    other, other_id = await _client(client, "otro@test.mx", "Otro")
    await playlists_service.add_member(session, uuid.UUID(member.playlist_id), other_id)
    r = await member.delete(f"/api/playlists/{member.playlist_id}/members/{other_id}")
    assert r.status_code == 403
    await other.aclose()


async def test_detail_lists_members_with_names(member, owner):
    detail = (await owner.get(f"/api/playlists/{member.playlist_id}")).json()
    assert detail["members"] == [{"user_id": str(member.user_id), "name": "Alex Colab"}]
