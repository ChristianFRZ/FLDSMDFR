import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.db import session_scope
from app.modules.social import service
from app.modules.social.models import Tape, TapeInvite, TapeMember
from tests.modules.social.test_tapes import add_track, make_tape, read


async def invite(client, user, tape, **kw):
    r = await client.post(f"/api/tapes/{tape['id']}/invites", json=kw or {"max_uses": 1}, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


async def join(client, user, token):
    return await client.post(f"/api/tapes/join/{token}", headers=user.headers)


async def preview(client, user, token):
    return await client.get(f"/api/tapes/invites/{token}", headers=user.headers)


async def pending(client, user):
    return (await client.get("/api/tapes/invites/pending", headers=user.headers)).json()


async def members(tape):
    async with session_scope() as session:
        return len(list((await session.execute(select(TapeMember).where(TapeMember.tape_id == tape["id"]))).scalars()))


async def test_any_member_can_invite(client, listener, make_user):
    guest, third = await make_user(), await make_user()
    tape = await make_tape(client, listener)
    await join(client, guest, (await invite(client, listener, tape))["token"])
    created = await invite(client, guest, tape)
    assert (await join(client, third, created["token"])).status_code == 200


async def test_non_member_cannot_invite(client, listener, make_user):
    other, tape = await make_user(), await make_tape(client, listener)
    r = await client.post(f"/api/tapes/{tape['id']}/invites", json={"max_uses": 1}, headers=other.headers)
    assert r.status_code == 403


async def test_token_is_stored_hashed(client, listener):
    tape = await make_tape(client, listener)
    created = await invite(client, listener, tape)
    async with session_scope() as session:
        stored = await session.scalar(select(TapeInvite.token_hash))
    assert created["token"] not in stored


async def test_many_uses_need_expiry_422(client, listener):
    tape = await make_tape(client, listener)
    r = await client.post(f"/api/tapes/{tape['id']}/invites", json={"max_uses": 3}, headers=listener.headers)
    assert r.status_code == 422


async def test_join_same_token_twice_idempotent(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape, max_uses=3, expires_in_hours=1)
    first = await join(client, guest, created["token"])
    second = await join(client, guest, created["token"])
    assert (first.status_code, second.status_code) == (200, 200)
    assert (first.json()["joined"], second.json()["joined"]) == (True, False)
    assert await members(tape) == 2
    async with session_scope() as session:
        assert await session.scalar(select(TapeInvite.uses)) == 1


async def test_rejoin_works_after_single_use_spent(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await join(client, guest, created["token"])
    assert (await join(client, guest, created["token"])).status_code == 200


async def test_last_use_race(client, listener, make_user):
    a, b = await make_user(), await make_user()
    tape = await make_tape(client, listener)
    created = await invite(client, listener, tape)
    r = await asyncio.gather(join(client, a, created["token"]), join(client, b, created["token"]))
    assert sorted(x.status_code for x in r) == [200, 409]
    assert await members(tape) == 2


async def test_member_8_race(client, listener, make_user):
    tape = await make_tape(client, listener)
    created = await invite(client, listener, tape, max_uses=20, expires_in_hours=1)
    for _ in range(6):
        await join(client, await make_user(), created["token"])
    a, b = await make_user(), await make_user()
    r = await asyncio.gather(join(client, a, created["token"]), join(client, b, created["token"]))
    assert sorted(x.status_code for x in r) == [200, 409]
    assert await members(tape) == 8


async def test_expired_or_revoked_invite_410(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    expired = await invite(client, listener, tape, max_uses=2, expires_in_hours=1)
    async with session_scope() as session:
        await session.execute(
            update(TapeInvite).where(TapeInvite.id == expired["id"]).values(expires_at=datetime.now(UTC) - timedelta(1))
        )
    revoked = await invite(client, listener, tape)
    url = f"/api/tapes/{tape['id']}/invites/{revoked['id']}"
    assert (await client.delete(url, headers=listener.headers)).status_code == 204
    for token in (expired["token"], revoked["token"]):
        assert (await join(client, guest, token)).status_code == 410
        assert (await preview(client, guest, token)).status_code == 410


async def test_unknown_token_404(client, listener):
    assert (await join(client, listener, "nada")).status_code == 404
    assert (await preview(client, listener, "nada")).status_code == 404


async def test_only_creator_revokes(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    await join(client, guest, (await invite(client, listener, tape))["token"])
    created = await invite(client, guest, tape)
    url = f"/api/tapes/{tape['id']}/invites/{created['id']}"
    assert (await client.delete(url, headers=guest.headers)).status_code == 403


async def test_preview_shows_only_title_and_inviter(client, listener, make_user, make_song):
    guest, tape = await make_user(), await make_tape(client, listener)
    await add_track(client, listener, tape, await make_song(), "Secreto")
    r = await preview(client, guest, (await invite(client, listener, tape))["token"])
    assert r.status_code == 200
    assert r.json()["title"] == "Para el viaje"
    assert r.json()["inviter"]
    assert r.json()["tape_id"] is None
    assert "Secreto" not in r.text
    assert "tracks" not in r.json()


async def test_preview_needs_session(client, listener):
    tape = await make_tape(client, listener)
    created = await invite(client, listener, tape)
    assert (await client.get(f"/api/tapes/invites/{created['token']}")).status_code == 401


async def test_opening_preview_creates_pending_claim(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    assert await pending(client, guest) == []
    await preview(client, guest, created["token"])
    items = await pending(client, guest)
    assert [i["title"] for i in items] == ["Para el viaje"]


async def test_preview_does_not_spend_uses(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await preview(client, guest, created["token"])
    await preview(client, guest, created["token"])
    assert (await join(client, guest, created["token"])).status_code == 200


async def test_member_preview_has_no_claim(client, listener):
    tape = await make_tape(client, listener)
    created = await invite(client, listener, tape)
    body = (await preview(client, listener, created["token"])).json()
    assert body["already_member"] is True
    assert body["tape_id"] == tape["id"]
    assert await pending(client, listener) == []


async def test_join_clears_pending(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await preview(client, guest, created["token"])
    await join(client, guest, created["token"])
    assert await pending(client, guest) == []


async def test_dismiss_clears_pending(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await preview(client, guest, created["token"])
    r = await client.post(f"/api/tapes/invites/{created['token']}/dismiss", headers=guest.headers)
    assert r.status_code == 204
    assert await pending(client, guest) == []


async def test_pending_acts_by_invite_id(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await preview(client, guest, created["token"])
    item = (await pending(client, guest))[0]
    assert "token" not in item
    r = await client.post(f"/api/tapes/claims/{item['invite_id']}/join", headers=guest.headers)
    assert r.status_code == 200
    assert (await read(client, guest, tape)).status_code == 200


async def test_pending_dismiss_by_invite_id(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await preview(client, guest, created["token"])
    item = (await pending(client, guest))[0]
    r = await client.post(f"/api/tapes/claims/{item['invite_id']}/dismiss", headers=guest.headers)
    assert r.status_code == 204
    assert await pending(client, guest) == []


async def test_claim_routes_need_own_claim(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    r = await client.post(f"/api/tapes/claims/{created['id']}/join", headers=guest.headers)
    assert r.status_code == 404


async def test_revoked_invite_leaves_pending(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await preview(client, guest, created["token"])
    await client.delete(f"/api/tapes/{tape['id']}/invites/{created['id']}", headers=listener.headers)
    assert await pending(client, guest) == []


async def test_creator_sees_invites_and_member_does_not(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    created = await invite(client, listener, tape)
    await join(client, guest, created["token"])
    assert (await read(client, listener, tape)).json()["invites"][0]["id"] == created["id"]
    assert (await read(client, guest, tape)).json()["invites"] == []


async def test_pending_invite_shows_in_notices(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    await preview(client, guest, (await invite(client, listener, tape))["token"])
    body = (await client.get("/api/notices", headers=guest.headers)).json()
    assert body["unread"] == 1
    assert body["items"][0]["type"] == "invite"
    assert body["items"][0]["title"] == "Para el viaje"


async def test_catalog_down_notices_keep_invites(client, listener, make_user, make_song, monkeypatch):
    guest, tape = await make_user(), await make_tape(client, listener)
    await preview(client, guest, (await invite(client, listener, tape))["token"])
    song = await make_song()
    await client.put(f"/api/follows/{song.artist_id}", headers=guest.headers)

    async def broken(*_):
        raise RuntimeError("catálogo caído")

    monkeypatch.setattr(service, "published_since", broken)
    body = (await client.get("/api/notices", headers=guest.headers)).json()
    assert body["degraded"] is True
    assert [i["type"] for i in body["items"]] == ["invite"]


async def test_deleting_tape_removes_pending(client, listener, make_user):
    guest, tape = await make_user(), await make_tape(client, listener)
    await preview(client, guest, (await invite(client, listener, tape))["token"])
    await client.delete(f"/api/tapes/{tape['id']}", headers=listener.headers)
    assert await pending(client, guest) == []
    async with session_scope() as session:
        assert await session.scalar(select(Tape.id)) is None
