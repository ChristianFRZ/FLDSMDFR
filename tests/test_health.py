from app.main import app
from app.shared.deps import get_session


async def test_health_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_degraded_when_database_fails(client):
    class BrokenSession:
        async def execute(self, *_args, **_kwargs):
            raise ConnectionError("db caida")

    async def broken_session():
        yield BrokenSession()

    app.dependency_overrides[get_session] = broken_session
    try:
        response = await client.get("/api/health")
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "error"}


async def test_unknown_api_route_is_json_404(client):
    response = await client.get("/api/no-existe")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
