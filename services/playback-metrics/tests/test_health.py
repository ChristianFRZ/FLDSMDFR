import httpx

NAMES = ["users-playlists", "catalog-streaming", "playback-metrics", "database", "jamendo", "aggregates"]


async def _health(client, admin) -> list[dict]:
    response = await client.get("/api/admin/health", headers=admin.headers)
    assert response.status_code == 200
    return response.json()["services"]


async def test_health_lists_three_services_plus_database_jamendo_aggregates(client, admin):
    services = await _health(client, admin)
    assert [s["name"] for s in services] == NAMES
    by_name = {s["name"]: s for s in services}
    assert by_name["users-playlists"]["status"] == "up"
    assert by_name["users-playlists"]["uptime_seconds"] == 120
    assert by_name["catalog-streaming"]["status"] == "up"
    assert by_name["playback-metrics"]["status"] == "up"
    assert by_name["playback-metrics"]["uptime_seconds"] >= 0
    assert by_name["database"]["status"] == "up"
    assert by_name["jamendo"] == {"name": "jamendo", "status": "up"}
    assert by_name["aggregates"]["status"] == "up"


async def test_health_marks_down_the_service_that_times_out(client, admin, fake_users, fake_catalog):
    fake_users.health_error = httpx.ReadTimeout("sin respuesta")
    services = {s["name"]: s for s in await _health(client, admin)}
    assert services["users-playlists"] == {"name": "users-playlists", "status": "down"}
    assert services["catalog-streaming"]["status"] == "up"
    assert services["playback-metrics"]["status"] == "up"


async def test_health_with_catalog_down_marks_it_and_jamendo_down(client, admin, fake_catalog):
    fake_catalog.down = True
    services = {s["name"]: s for s in await _health(client, admin)}
    assert services["catalog-streaming"] == {"name": "catalog-streaming", "status": "down"}
    assert services["jamendo"]["status"] == "down"
