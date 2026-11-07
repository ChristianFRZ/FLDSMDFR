import asyncio

from sqlalchemy import text

from app.core.db import get_engine
from app.modules.users.public import record_audit, user_growth


async def count_active_admins():
    async with get_engine().connect() as conn:
        q = text("SELECT count(*) FROM users WHERE role='admin' AND status='active'")
        return (await conn.execute(q)).scalar()


def demote(client, actor, target):
    return client.post(f"/api/admin/users/{target.id}/role", json={"role": "listener"}, headers=actor.headers)


async def test_cannot_demote_last_admin(client, admin):
    r = await demote(client, admin, admin)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin"
    assert await count_active_admins() == 1


async def test_rejected_attempt_is_audited(client, admin):
    await demote(client, admin, admin)
    rows = (await client.get("/api/admin/audit?action=role_change", headers=admin.headers)).json()["items"]
    assert rows[0]["outcome"] == "rejected"
    assert rows[0]["actor_id"] == admin.id


async def test_two_admins_demote_each_other_concurrently(client, make_user):
    a, b = await make_user(role="admin"), await make_user(role="admin")
    r1, r2 = await asyncio.gather(demote(client, a, b), demote(client, b, a))
    codes = sorted([r1.status_code, r2.status_code])
    # El perdedor ya no es administrador: recibe 403, o 409 si le gana a la revisión de rol.
    assert codes[0] == 200 and codes[1] in (403, 409)
    assert await count_active_admins() == 1


async def test_cannot_suspend_last_admin(client, admin):
    r = await client.post(f"/api/admin/users/{admin.id}/suspend", json={"reason": "x"}, headers=admin.headers)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_admin"


async def test_suspended_admin_does_not_count_as_active(client, make_user):
    a, b = await make_user(role="admin"), await make_user(role="admin")
    r = await client.post(f"/api/admin/users/{b.id}/suspend", json={"reason": "x"}, headers=a.headers)
    assert r.status_code == 200
    assert (await demote(client, a, a)).status_code == 409


async def test_promote_to_admin_and_audit(client, admin, listener):
    r = await client.post(f"/api/admin/users/{listener.id}/role", json={"role": "admin"}, headers=admin.headers)
    assert r.status_code == 200
    assert (await client.get("/api/users/me", headers=listener.headers)).json()["role"] == "admin"
    row = (await client.get("/api/admin/audit", headers=admin.headers)).json()["items"][0]
    assert row["action"] == "role_change"
    assert row["target_id"] == listener.id
    assert row["detail"] == {"from": "listener", "to": "admin"}


async def test_invalid_role_422(client, admin, listener):
    r = await client.post(f"/api/admin/users/{listener.id}/role", json={"role": "rey"}, headers=admin.headers)
    assert r.status_code == 422


async def test_suspend_blocks_at_once_and_reactivate_restores(client, admin, listener):
    r = await client.post(f"/api/admin/users/{listener.id}/suspend", json={"reason": "spam"}, headers=admin.headers)
    assert r.status_code == 200
    assert (await client.get("/api/users/me", headers=listener.headers)).status_code == 401
    await client.post(f"/api/admin/users/{listener.id}/reactivate", headers=admin.headers)
    assert (await client.get("/api/users/me", headers=listener.headers)).status_code == 200


async def test_admin_routes_403_for_others(client, make_user):
    for role in ("listener", "composer"):
        u = await make_user(role=role)
        for path in ("/api/admin/audit", "/api/admin/users", "/api/admin/composer-requests"):
            assert (await client.get(path, headers=u.headers)).status_code == 403


async def test_audit_is_read_only(client, admin):
    for method in ("put", "patch", "delete", "post"):
        r = await getattr(client, method)("/api/admin/audit", headers=admin.headers)
        assert r.status_code == 405


async def test_audit_filter_and_pagination(client, admin):
    for i in range(3):
        await record_audit(admin.id, "hide_song", "song", f"s{i}")
    await record_audit(admin.id, "role_change", "user", "u1")
    r = (await client.get("/api/admin/audit?action=hide_song&page=1&size=2", headers=admin.headers)).json()
    assert r["total"] == 3
    assert len(r["items"]) == 2
    assert all(i["action"] == "hide_song" for i in r["items"])


async def test_users_list_filters(client, admin, listener):
    r = (await client.get("/api/admin/users?role=admin", headers=admin.headers)).json()
    assert [u["id"] for u in r["items"]] == [admin.id]
    r = (await client.get(f"/api/admin/users?q={listener.email[:5]}", headers=admin.headers)).json()
    assert [u["id"] for u in r["items"]] == [listener.id]


async def test_user_growth_counts_by_role(admin, listener):
    points = await user_growth(days=7)
    today = points[-1]
    assert today.listener == 1
    assert today.admin == 1
    assert today.composer == 0
    assert len(points) == 7
