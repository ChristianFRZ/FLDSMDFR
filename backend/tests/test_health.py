from app.core.errors import AppError


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_error_shape(app, client):
    @app.get("/api/health/boom")
    async def boom():
        raise AppError(418, "teapot", "x")

    r = await client.get("/api/health/boom")
    assert r.status_code == 418
    assert r.json() == {"error": {"code": "teapot", "message": "x", "detail": None}}


async def test_validation_errors_use_same_shape(app, client):
    @app.get("/api/health/need")
    async def need(n: int):
        return n

    r = await client.get("/api/health/need?n=x")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


async def test_unknown_api_route_uses_same_shape(client):
    r = await client.get("/api/no-existe")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
