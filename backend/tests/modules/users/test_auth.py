import time

import pytest
from sqlalchemy import text

from app.core.db import get_engine
from app.core.security import decode_token
from app.modules.users.public import ensure_first_admin


async def set_status(user_id, status):
    async with get_engine().begin() as conn:
        await conn.execute(text("UPDATE users SET status=:s WHERE id=:i"), {"s": status, "i": user_id})


def body(email="a@example.com", password="secreto123"):
    return {"email": email, "password": password, "display_name": "Ana"}


async def test_register_returns_jwt_claims(client):
    r = await client.post("/api/auth/register", json=body())
    assert r.status_code == 201
    claims = decode_token(r.json()["access_token"])
    assert {"sub", "role", "exp"} <= claims.keys()
    assert claims["role"] == "listener"
    assert claims["exp"] - time.time() <= 15 * 60


async def test_register_cannot_choose_role(client):
    r = await client.post("/api/auth/register", json={**body(), "role": "admin"})
    assert decode_token(r.json()["access_token"])["role"] == "listener"


async def test_duplicate_email_409(client):
    await client.post("/api/auth/register", json=body())
    r = await client.post("/api/auth/register", json=body(email="A@EXAMPLE.com"))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


async def test_short_password_422(client):
    assert (await client.post("/api/auth/register", json=body(password="corta"))).status_code == 422


async def test_login_ok(client, make_user):
    u = await make_user()
    r = await client.post("/api/auth/login", json={"email": u.email, "password": u.password})
    assert r.status_code == 200
    assert decode_token(r.json()["access_token"])["sub"] == u.id


async def test_wrong_password_401(client, make_user):
    u = await make_user()
    r = await client.post("/api/auth/login", json={"email": u.email, "password": "otra-clave"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


async def test_unknown_email_same_error_as_wrong_password(client):
    r = await client.post("/api/auth/login", json={"email": "nadie@example.com", "password": "otra-clave"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


async def test_login_rate_limit(client, make_user):
    u = await make_user()
    attempt = {"email": u.email, "password": "otra-clave"}
    for _ in range(5):
        assert (await client.post("/api/auth/login", json=attempt)).status_code == 401
    assert (await client.post("/api/auth/login", json=attempt)).status_code == 429
    good = await client.post("/api/auth/login", json={"email": u.email, "password": u.password})
    assert good.status_code == 429


async def test_refresh_rotates(client):
    first = (await client.post("/api/auth/register", json=body())).json()
    r = await client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["refresh_token"] != first["refresh_token"]
    again = await client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert again.status_code == 401


async def test_logout_revokes_refresh(client):
    t = (await client.post("/api/auth/register", json=body())).json()
    assert (await client.post("/api/auth/logout", json={"refresh_token": t["refresh_token"]})).status_code == 204
    r = await client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 401


async def test_me_requires_token(client):
    assert (await client.get("/api/users/me")).status_code == 401


async def test_garbage_token_401(client):
    r = await client.get("/api/users/me", headers={"Authorization": "Bearer basura"})
    assert r.status_code == 401


async def test_edit_profile_only_changes_display_name(client, make_user):
    u = await make_user()
    r = await client.patch("/api/users/me", json={"display_name": "Nuevo", "role": "admin"}, headers=u.headers)
    assert r.status_code == 200
    assert r.json()["display_name"] == "Nuevo"
    assert r.json()["role"] == "listener"


async def test_suspended_user_blocked_immediately(client, make_user):
    u = await make_user()
    await set_status(u.id, "suspended")
    assert (await client.get("/api/users/me", headers=u.headers)).status_code == 401


async def test_suspended_user_cannot_login_or_refresh(client):
    t = (await client.post("/api/auth/register", json=body())).json()
    me = (await client.get("/api/users/me", headers={"Authorization": f"Bearer {t['access_token']}"})).json()
    await set_status(me["id"], "suspended")
    r = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "secreto123"})
    assert r.status_code == 403
    assert (await client.post("/api/auth/refresh", json={"refresh_token": t["refresh_token"]})).status_code == 401


async def test_role_comes_from_db_not_token(client, make_user):
    u = await make_user(role="admin")
    assert decode_token(u.token)["role"] == "listener"
    assert (await client.get("/api/users/me", headers=u.headers)).json()["role"] == "admin"


@pytest.mark.parametrize("calls", [1, 2])
async def test_first_admin_seeded_once(calls):
    for _ in range(calls):
        await ensure_first_admin("root@example.com", "clave-admin")
    async with get_engine().connect() as conn:
        n = (await conn.execute(text("SELECT count(*) FROM users WHERE role='admin'"))).scalar()
    assert n == 1


async def test_first_admin_can_login(client):
    await ensure_first_admin("root@meloxo.local", "clave-admin")
    r = await client.post("/api/auth/login", json={"email": "root@meloxo.local", "password": "clave-admin"})
    assert r.status_code == 200
