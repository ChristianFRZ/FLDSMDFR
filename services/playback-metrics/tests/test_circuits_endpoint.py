"""Estado de los circuitos de este servicio, solo para administradores."""

import pytest

from app.clients import users
from app.clients.http import RemoteUnavailable
from tests.helpers import make_admin_client, signup


async def test_circuits_anonymous_401(client):
    assert (await client.get("/api/metrics/circuits")).status_code == 401


async def test_circuits_listener_403(client):
    await signup(client)
    assert (await client.get("/api/metrics/circuits")).status_code == 403


async def test_circuits_admin_shape(client, session, take_down):
    admin = await make_admin_client(session, client)
    take_down("users-playlists")
    for _ in range(5):
        with pytest.raises(RemoteUnavailable):
            await users.count_users()
    r = await admin.get("/api/metrics/circuits")
    assert r.status_code == 200
    body = r.json()
    assert body["instance"].startswith("playback-metrics-")
    circuit = next(c for c in body["circuits"] if c["target"] == "users-playlists")
    assert circuit["source"] == "playback-metrics"
    assert circuit["state"] == "open"
    assert circuit["consecutive_failures"] == 5
    assert 0 < circuit["retry_in_s"] <= 10
