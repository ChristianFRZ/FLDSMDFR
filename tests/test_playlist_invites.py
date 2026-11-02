import uuid

import pytest
from httpx import AsyncClient

from app.modules.playlists import service as playlists_service
from tests.helpers import signup


@pytest.fixture
async def owner(client):
    await signup(client, email="duena@test.mx", name="Marta Ruiz")
    r = await client.post("/api/playlists", json={"name": "Tardes de verano"})
    client.playlist_id = r.json()["id"]
    return client


@pytest.fixture
async def guest(client):
    c = AsyncClient(transport=client._transport, base_url="http://test")
    body = await signup(c, email="invitada@test.mx", name="Alex")
    c.user_id = uuid.UUID(body["user"]["id"])
    yield c
    await c.aclose()


async def _link(owner) -> dict:
    r = await owner.post(f"/api/playlists/{owner.playlist_id}/invites")
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_link_and_claim_creates_pending(owner, guest, session):
    link = await _link(owner)
    assert link["url"] == f"/invitacion/{link['token']}"
    r = await guest.post(f"/api/invites/{link['token']}/claim")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "playlist_id": owner.playlist_id,
        "playlist_name": "Tardes de verano",
        "status": "pending",
    }
    pending = await playlists_service.pending_invites_for(session, guest.user_id)
    assert [(p.token, p.playlist_name) for p in pending] == [(link["token"], "Tardes de verano")]


async def test_claim_is_idempotent(owner, guest, session):
    link = await _link(owner)
    await guest.post(f"/api/invites/{link['token']}/claim")
    r = await guest.post(f"/api/invites/{link['token']}/claim")
    assert r.status_code == 200
    assert len(await playlists_service.pending_invites_for(session, guest.user_id)) == 1


async def test_accept_makes_member(owner, guest, session):
    link = await _link(owner)
    await guest.post(f"/api/invites/{link['token']}/claim")
    r = await guest.post(f"/api/invites/{link['token']}/accept")
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "collaborator"
    assert [p["id"] for p in (await guest.get("/api/playlists")).json()] == [owner.playlist_id]
    assert await playlists_service.pending_invites_for(session, guest.user_id) == []


async def test_ignore_removes_from_pending(owner, guest, session):
    link = await _link(owner)
    await guest.post(f"/api/invites/{link['token']}/claim")
    r = await guest.post(f"/api/invites/{link['token']}/ignore")
    assert r.status_code == 204
    assert await playlists_service.pending_invites_for(session, guest.user_id) == []
    assert (await guest.get("/api/playlists")).json() == []


async def test_accept_without_claim_404(owner, guest):
    link = await _link(owner)
    r = await guest.post(f"/api/invites/{link['token']}/accept")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "invite_not_found"


async def test_new_link_revokes_old(owner, guest):
    old = await _link(owner)
    await _link(owner)
    r = await guest.post(f"/api/invites/{old['token']}/claim")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "invite_not_found"


async def test_revoked_link_404(owner, guest, session):
    link = await _link(owner)
    await guest.post(f"/api/invites/{link['token']}/claim")
    assert (await owner.delete(f"/api/playlists/{owner.playlist_id}/invites")).status_code == 204
    r = await guest.post(f"/api/invites/{link['token']}/claim")
    assert r.status_code == 404
    assert await playlists_service.pending_invites_for(session, guest.user_id) == []


async def test_owner_claim_returns_member_status(owner, session):
    link = await _link(owner)
    r = await owner.post(f"/api/invites/{link['token']}/claim")
    assert r.status_code == 200
    assert r.json()["status"] == "member"
    assert r.json()["playlist_id"] == owner.playlist_id


async def test_member_claim_returns_member_status_without_pending(owner, guest, session):
    link = await _link(owner)
    await guest.post(f"/api/invites/{link['token']}/claim")
    await guest.post(f"/api/invites/{link['token']}/accept")
    r = await guest.post(f"/api/invites/{link['token']}/claim")
    assert r.status_code == 200
    assert r.json()["status"] == "member"
    assert await playlists_service.pending_invites_for(session, guest.user_id) == []


async def test_reclaim_after_ignore_is_pending_again(owner, guest, session):
    link = await _link(owner)
    await guest.post(f"/api/invites/{link['token']}/claim")
    await guest.post(f"/api/invites/{link['token']}/ignore")
    r = await guest.post(f"/api/invites/{link['token']}/claim")
    assert r.json()["status"] == "pending"
    assert len(await playlists_service.pending_invites_for(session, guest.user_id)) == 1


async def test_non_owner_cannot_create_link(owner, guest):
    r = await guest.post(f"/api/playlists/{owner.playlist_id}/invites")
    assert r.status_code == 404
