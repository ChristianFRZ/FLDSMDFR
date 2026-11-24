import httpx
from fastapi import FastAPI

from meloxo_common.errors import AppError, register_error_handlers


def _app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    async def boom():
        raise AppError(409, "conflict", "Choque", {"x": 1})

    @app.get("/n")
    async def n(size: int):
        return size

    return app


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        return await client.get(path)


async def test_app_error_body_format():
    r = await _get("/boom")
    assert r.status_code == 409
    assert r.json() == {"error": {"code": "conflict", "message": "Choque", "detail": {"x": 1}}}


async def test_validation_error_body_format():
    r = await _get("/n?size=abc")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


async def test_unknown_route_is_not_found():
    r = await _get("/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
