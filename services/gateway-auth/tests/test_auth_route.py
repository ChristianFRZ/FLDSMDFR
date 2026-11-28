from datetime import timedelta

import pytest

from meloxo_common.security import encode_token


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_valid_token_returns_204_with_identity_headers(client, make_token):
    user_id, token = make_token("listener")
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 204
    assert response.headers["x-user-id"] == user_id
    assert response.headers["x-user-role"] == "listener"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic x"}, {"Authorization": "Bearer basura"}])
async def test_missing_or_malformed_authorization_is_401(client, headers):
    response = await client.get("/auth", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_expired_token_is_401(client, fake_users):
    user_id = fake_users.add_user()
    token = encode_token({"sub": str(user_id)}, timedelta(seconds=-10))
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_malformed_subject_is_401(client):
    token = encode_token({"sub": "no-es-uuid"}, timedelta(minutes=5))
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 401


async def test_suspended_user_is_401(client, make_token):
    _, token = make_token(status="suspended")
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_unknown_user_is_401(client):
    from uuid import uuid4

    token = encode_token({"sub": str(uuid4())}, timedelta(minutes=5))
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 401


async def test_stream_ticket_is_not_a_session(client, fake_users):
    user_id = fake_users.add_user()
    token = encode_token({"sub": str(user_id), "scope": "stream"}, timedelta(minutes=5))
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 401


async def test_role_not_allowed_is_403(client, make_token):
    _, listener = make_token("listener")
    response = await client.get("/auth", headers={**bearer(listener), "X-Required-Roles": "admin"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"

    _, composer = make_token("composer")
    response = await client.get("/auth", headers={**bearer(composer), "X-Required-Roles": "composer,admin"})
    assert response.status_code == 204

    _, admin = make_token("admin")
    response = await client.get("/auth", headers={**bearer(admin), "X-Required-Roles": "composer,admin"})
    assert response.status_code == 204
    response = await client.get("/auth", headers={**bearer(admin), "X-Required-Roles": "admin"})
    assert response.status_code == 204


async def test_empty_required_roles_means_any_role(client, make_token):
    _, token = make_token("listener")
    response = await client.get("/auth", headers={**bearer(token), "X-Required-Roles": ""})
    assert response.status_code == 204


async def test_users_playlists_down_is_503(client, fake_users, make_token):
    _, token = make_token()
    fake_users.down = True
    response = await client.get("/auth", headers=bearer(token))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "upstream_unavailable"


async def test_health_needs_no_auth(client):
    response = await client.get("/internal/health")
    assert response.status_code == 200
    assert response.json() == {"status": "up"}
