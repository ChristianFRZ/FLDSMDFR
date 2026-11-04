"""Gateway en 04: límite corto solo para conectar y un reintento en otra réplica si no conectó."""

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import proxy
from app.shared import discovery
from tests.conftest import upstream


class Recording(httpx.AsyncBaseTransport):
    """La red: registra a qué IP se intentó llamar; `dead` rechaza y `slow` agota la conexión."""

    def __init__(self):
        self.apps: dict[str, httpx.ASGITransport] = {}
        self.timeouts: set[str] = set()
        self.hits: list[str] = []

    def add(self, host: str, app: FastAPI) -> None:
        self.apps[host] = httpx.ASGITransport(app=app)

    async def handle_async_request(self, request):
        host = request.url.host
        self.hits.append(host)
        if host in self.timeouts:
            raise httpx.ConnectTimeout("sin respuesta al conectar", request=request)
        if host not in self.apps:
            raise httpx.ConnectError("instancia muerta", request=request)
        return await self.apps[host].handle_async_request(request)


def _failing() -> FastAPI:
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def boom(path: str):
        return JSONResponse({"error": {"code": "internal", "message": "x"}}, status_code=500)

    return app


@pytest.fixture
def net(consul, monkeypatch):
    rec = Recording()
    proxy.set_network_transport(rec)
    monkeypatch.setattr(proxy, "retry_wait", lambda: 0)
    monkeypatch.setattr(proxy, "_balancer", discovery.RoundRobin())  # empieza por la primera
    consul.add("catalog-streaming", "catalog-streaming-a", "10.0.4.1")
    consul.add("catalog-streaming", "catalog-streaming-b", "10.0.4.2")
    yield rec
    proxy.set_network_transport(None)


async def test_get_retried_on_connect_error(client, net):
    net.add("10.0.4.2", upstream("b"))  # 10.0.4.1 está muerta
    r = await client.get("/api/songs")
    assert r.status_code == 200
    assert r.json()["label"] == "b"
    assert net.hits == ["10.0.4.1", "10.0.4.2"]


async def test_connect_timeout_retried(client, net):
    net.timeouts.add("10.0.4.1")
    net.add("10.0.4.2", upstream("b"))
    r = await client.get("/api/songs")
    assert r.status_code == 200
    assert net.hits == ["10.0.4.1", "10.0.4.2"]


async def test_post_not_retried_on_connect_error(client, net):
    net.add("10.0.4.2", upstream("b"))
    r = await client.post("/api/songs", content=b"x" * 10)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"
    assert net.hits == ["10.0.4.1"]


async def test_5xx_not_retried(client, net):
    net.add("10.0.4.1", _failing())
    net.add("10.0.4.2", upstream("b"))
    r = await client.get("/api/songs")
    assert r.status_code == 500
    assert net.hits == ["10.0.4.1"]


async def test_both_dead_503(client, net):
    r = await client.get("/api/songs")
    assert r.status_code == 503
    assert len(net.hits) == 2


def test_client_timeouts_configured():
    proxy.set_network_transport(None)
    timeout = proxy._http().timeout
    assert (timeout.connect, timeout.read, timeout.write) == (1.5, 30, 30)
