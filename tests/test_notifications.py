import pytest
from httpx import AsyncClient

from app.modules.catalog import service as catalog_service
from tests.audio_fixtures import insert_song
from tests.helpers import signup


@pytest.fixture
async def user(client):
    await signup(client, email="oyente@test.mx", name="Alex")
    return client


async def _notices(c) -> dict:
    r = await c.get("/api/me/notifications")
    assert r.status_code == 200, r.text
    return r.json()


async def _follow_then_release(user, session, media_dir):
    await insert_song(session, media_dir, title="Vieja", artist="Natalia Lafourcade")
    await user.put("/api/me/follows/Natalia Lafourcade")
    return await insert_song(
        session, media_dir, title="Pajarito colibrí", artist="Natalia Lafourcade"
    )


async def test_release_notice_for_followed_artist(user, session, media_dir):
    nueva = await _follow_then_release(user, session, media_dir)
    data = await _notices(user)
    assert data["unread_count"] == 1
    [n] = data["items"]
    assert n["id"] == f"release:{nueva.id}"
    assert n["type"] == "release"
    assert n["read"] is False
    assert n["song"]["title"] == "Pajarito colibrí"
    assert n["invite"] is None


async def test_no_notice_for_song_before_follow(user, session, media_dir):
    await insert_song(session, media_dir, artist="Masego")
    await user.put("/api/me/follows/Masego")
    assert (await _notices(user)) == {"items": [], "unread_count": 0}


async def test_inactive_release_not_listed(user, session, media_dir):
    nueva = await _follow_then_release(user, session, media_dir)
    await catalog_service.deactivate_song(session, nueva.id)
    assert (await _notices(user))["items"] == []


async def test_invite_notice_after_claim_with_inviter_name(user, client):
    owner = AsyncClient(transport=client._transport, base_url="http://test")
    await signup(owner, email="marta@test.mx", name="Marta R.")
    pid = (await owner.post("/api/playlists", json={"name": "Tardes de verano"})).json()["id"]
    token = (await owner.post(f"/api/playlists/{pid}/invites")).json()["token"]
    await user.post(f"/api/invites/{token}/claim")
    [n] = (await _notices(user))["items"]
    assert n["id"] == f"invite:{token}"
    assert n["type"] == "invite"
    assert n["invite"] == {
        "token": token,
        "playlist_id": pid,
        "playlist_name": "Tardes de verano",
        "inviter_name": "Marta R.",
    }
    await user.post(f"/api/invites/{token}/accept")
    assert (await _notices(user))["items"] == []
    await owner.aclose()


async def test_mark_read_updates_unread_count(user, session, media_dir):
    nueva = await _follow_then_release(user, session, media_dir)
    nid = f"release:{nueva.id}"
    r = await user.post("/api/me/notifications/read", json={"ids": [nid]})
    assert r.status_code == 204
    assert (await user.post("/api/me/notifications/read", json={"ids": [nid]})).status_code == 204
    data = await _notices(user)
    assert data["unread_count"] == 0
    assert data["items"][0]["read"] is True


async def test_mark_read_validates_ids(user):
    r = await user.post("/api/me/notifications/read", json={"ids": ["x" * 121]})
    assert r.status_code == 422
    r = await user.post("/api/me/notifications/read", json={"ids": ["a"] * 101})
    assert r.status_code == 422
