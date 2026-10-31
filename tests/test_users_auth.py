import time
import uuid

import jwt
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from tests.helpers import make_admin_client, signup


async def test_register_sets_cookie_and_returns_listener(client):
    r = await client.post(
        "/api/auth/register",
        json={"name": "Ana", "email": "ana@test.mx", "password": "secreta123"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "listener"
    assert r.json()["token_type"] == "bearer"
    assert "fldsmdfr_session" in client.cookies


async def test_register_duplicate_email_conflict(client):
    await signup(client, email="ana@test.mx")
    r = await client.post(
        "/api/auth/register",
        json={"name": "Otra", "email": "ANA@Test.mx", "password": "secreta123"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


async def test_register_short_password_rejected(client):
    r = await client.post(
        "/api/auth/register",
        json={"name": "Ana", "email": "ana@test.mx", "password": "corta"},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_input"


async def test_login_wrong_password(client):
    await signup(client)
    r = await client.post(
        "/api/auth/login", json={"email": "oyente@test.mx", "password": "incorrecta1"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_me_with_cookie(client):
    await signup(client)
    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "oyente@test.mx"


async def test_me_with_bearer(client):
    token = (await signup(client))["access_token"]
    client.cookies.clear()
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


async def test_me_without_token(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_tampered_token_is_401(client):
    client.cookies.set("fldsmdfr_session", "abc.def.ghi")
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_expired_token_is_401(client):
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "listener", "exp": int(time.time()) - 60},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


async def test_listener_cannot_list_users(client):
    await signup(client)
    r = await client.get("/api/users")
    assert r.status_code == 403


async def test_admin_lists_and_promotes(session, client):
    listener = (await signup(client))["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        admin = await make_admin_client(session, other)
        try:
            listed = await admin.get("/api/users", params={"q": "oyente"})
            assert listed.status_code == 200
            assert [u["id"] for u in listed.json()] == [listener["id"]]
            r = await admin.patch(f"/api/users/{listener['id']}/role", json={"role": "admin"})
            assert r.status_code == 200
            assert r.json()["role"] == "admin"
        finally:
            await admin.aclose()


async def test_admin_cannot_demote_self(session, client):
    admin = await make_admin_client(session, client)
    try:
        me = (await admin.get("/api/auth/me")).json()
        r = await admin.patch(f"/api/users/{me['id']}/role", json={"role": "listener"})
        assert r.status_code == 403
    finally:
        await admin.aclose()


async def test_logout_clears_cookie(client):
    await signup(client)
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_reissues_cookie_after_promotion(session, client):
    listener = (await signup(client))["user"]
    assert (await client.get("/api/users")).status_code == 403
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        admin = await make_admin_client(session, other)
        try:
            r = await admin.patch(f"/api/users/{listener['id']}/role", json={"role": "admin"})
            assert r.status_code == 200
        finally:
            await admin.aclose()

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert get_settings().cookie_name in me.headers.get("set-cookie", "")
    assert (await client.get("/api/users")).status_code == 200


async def test_me_reissues_cookie_after_demotion(session, client):
    promoted = (await signup(client, email="otro@test.mx"))["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        admin = await make_admin_client(session, other)
        try:
            await admin.patch(f"/api/users/{promoted['id']}/role", json={"role": "admin"})
            relogin = await client.post(
                "/api/auth/login", json={"email": "otro@test.mx", "password": "secreta123"}
            )
            assert relogin.json()["user"]["role"] == "admin"
            assert (await client.get("/api/users")).status_code == 200
            await admin.patch(f"/api/users/{promoted['id']}/role", json={"role": "listener"})
        finally:
            await admin.aclose()

    me = await client.get("/api/auth/me")
    assert me.json()["role"] == "listener"
    assert (await client.get("/api/users")).status_code == 403


async def test_me_does_not_reissue_cookie_when_role_matches(client):
    await signup(client)
    me = await client.get("/api/auth/me")
    assert "set-cookie" not in me.headers
