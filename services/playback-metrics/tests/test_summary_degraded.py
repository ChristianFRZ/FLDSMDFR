"""El resumen del administrador se degrada: lo que no responde queda en null."""

from tests.helpers import make_admin_client


async def test_summary_ok_not_degraded(client, session):
    admin = await make_admin_client(session, client)
    body = (await admin.get("/api/metrics/summary")).json()
    assert body["degraded"] is False
    assert isinstance(body["total_users"], int)


async def test_summary_users_down_null(client, session, take_down):
    admin = await make_admin_client(session, client)
    take_down("users-playlists")
    r = await admin.get("/api/metrics/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_users"] is None
    assert isinstance(body["total_songs"], int)
    assert body["degraded"] is True


async def test_summary_catalog_down_null(client, session, take_down):
    admin = await make_admin_client(session, client)
    take_down("catalog-streaming")
    r = await admin.get("/api/metrics/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_songs"] is None
    assert isinstance(body["total_users"], int)
    assert body["degraded"] is True
