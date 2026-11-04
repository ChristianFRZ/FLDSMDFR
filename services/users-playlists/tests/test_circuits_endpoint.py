"""Estado de los circuitos de este servicio, solo para administradores."""

import uuid

import pytest

from app.clients import catalog
from app.clients.http import RemoteUnavailable
from tests.helpers import make_admin_client, signup


async def test_circuits_anonymous_401(client):
    assert (await client.get("/api/admin/circuits")).status_code == 401


async def test_circuits_listener_403(client):
    await signup(client)
    assert (await client.get("/api/admin/circuits")).status_code == 403


async def test_circuits_admin_shape(client, session, catalog_down):
    admin = await make_admin_client(session, client)
    for _ in range(5):
        with pytest.raises(RemoteUnavailable):
            await catalog.get_song(uuid.uuid4())
    r = await admin.get("/api/admin/circuits")
    assert r.status_code == 200
    body = r.json()
    assert body["instance"].startswith("users-playlists-")
    [circuit] = body["circuits"]
    assert circuit["source"] == "users-playlists"
    assert circuit["target"] == "catalog-streaming"
    assert circuit["state"] == "open"
    assert circuit["consecutive_failures"] == 5
    assert 0 < circuit["retry_in_s"] <= 10
