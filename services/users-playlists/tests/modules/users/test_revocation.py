from meloxo_common.redis_client import override_redis
from sqlalchemy import text

from meloxo_common.db import get_engine


def key(user) -> str:
    return f"revoked_after:{user.id}"


async def change_role(client, actor, target, role="composer"):
    return await client.post(f"/api/admin/users/{target.id}/role", json={"role": role}, headers=actor.headers)


async def test_set_role_writes_revocation(client, fake_redis, admin, listener):
    assert (await change_role(client, admin, listener)).status_code == 200
    assert await fake_redis.get(key(listener)) is not None


async def test_suspend_writes_revocation(client, fake_redis, admin, listener):
    r = await client.post(f"/api/admin/users/{listener.id}/suspend", json={"reason": "x"}, headers=admin.headers)
    assert r.status_code == 200
    assert await fake_redis.get(key(listener)) is not None


async def test_approve_composer_request_writes_revocation(client, fake_redis, admin, listener):
    rid = (await client.post("/api/composer-requests", json={"message": "hago música"}, headers=listener.headers)).json()["id"]
    r = await client.post(f"/api/admin/composer-requests/{rid}/approve", json={}, headers=admin.headers)
    assert r.status_code == 200
    assert await fake_redis.get(key(listener)) is not None


async def test_reactivate_does_not_write_revocation(client, fake_redis, admin, listener):
    await client.post(f"/api/admin/users/{listener.id}/suspend", json={"reason": "x"}, headers=admin.headers)
    await fake_redis.flushall()
    r = await client.post(f"/api/admin/users/{listener.id}/reactivate", headers=admin.headers)
    assert r.status_code == 200
    assert await fake_redis.get(key(listener)) is None


async def test_failed_last_admin_change_does_not_write_revocation(client, fake_redis, admin):
    r = await change_role(client, admin, admin, role="listener")
    assert r.status_code == 409
    assert await fake_redis.get(key(admin)) is None


async def test_admin_action_succeeds_when_redis_fails(client, admin, listener):
    class Down:
        async def set(self, *a, **k):
            raise ConnectionError("caído")

    override_redis(Down())
    assert (await change_role(client, admin, listener)).status_code == 200
    async with get_engine().connect() as conn:
        role = (await conn.execute(text("SELECT role FROM users WHERE id=:i"), {"i": listener.id})).scalar()
    assert role == "composer"


async def test_old_token_is_rejected_after_role_change(client, admin, listener):
    await change_role(client, admin, listener)
    r = await client.get("/api/users/me", headers=listener.headers)
    assert r.status_code == 401


async def test_refresh_after_role_change_gives_token_that_passes(client, admin):
    reg = await client.post(
        "/api/auth/register", json={"email": "ren@example.com", "password": "secreto123", "display_name": "ren"}
    )
    tokens = reg.json()
    me = (await client.get("/api/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})).json()
    await client.post(f"/api/admin/users/{me['id']}/role", json={"role": "composer"}, headers=admin.headers)

    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    fresh = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    r = await client.get("/api/users/me", headers=fresh)
    assert r.status_code == 200 and r.json()["role"] == "composer"
