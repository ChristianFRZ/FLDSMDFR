import os

os.environ.setdefault("FLDSMDFR_DISCOVERY_ENABLED", "false")

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi import FastAPI, Request, Response  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app import proxy  # noqa: E402
from app.main import app  # noqa: E402
from app.shared import discovery  # noqa: E402
from tests.fake_consul import FakeConsul  # noqa: E402

AUDIO = bytes(range(256)) * 16  # 4096 bytes


def upstream(label: str) -> FastAPI:
    """Servicio falso: dice quién contestó y qué recibió."""
    svc = FastAPI()

    @svc.get("/api/songs/{song_id}/stream")
    async def stream(request: Request):
        start, end = 0, 1023
        assert request.headers.get("range") == "bytes=0-1023"
        return Response(
            AUDIO[start : end + 1],
            status_code=206,
            media_type="audio/mpeg",
            headers={"Content-Range": f"bytes 0-1023/{len(AUDIO)}", "Accept-Ranges": "bytes"},
        )

    @svc.post("/api/auth/login")
    async def login():
        r = JSONResponse({"ok": True})
        r.set_cookie("fldsmdfr_session", "token")
        r.set_cookie("otra", "valor")
        return r

    @svc.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def echo(path: str, request: Request):
        body = await request.body()
        return JSONResponse(
            {"label": label, "path": f"/{path}", "query": request.url.query, "bytes": len(body)},
            headers={"X-Instancia": label},
        )

    return svc


class Network(httpx.AsyncBaseTransport):
    """La red interna: cada IP del directorio es un servicio falso."""

    def __init__(self) -> None:
        self.hosts: dict[str, httpx.ASGITransport] = {}

    def add(self, host: str, label: str) -> None:
        self.hosts[host] = httpx.ASGITransport(app=upstream(label))

    async def handle_async_request(self, request):
        transport = self.hosts.get(request.url.host)
        if transport is None:
            raise httpx.ConnectError("instancia muerta", request=request)
        return await transport.handle_async_request(request)


@pytest.fixture
def consul() -> FakeConsul:
    fake = FakeConsul()
    discovery.set_consul_transport(httpx.ASGITransport(app=fake.app))
    discovery.reset()
    yield fake
    discovery.reset()
    discovery.set_consul_transport(None)


@pytest.fixture
def network() -> Network:
    net = Network()
    proxy.set_network_transport(net)
    yield net
    proxy.set_network_transport(None)


@pytest.fixture
def cluster(consul, network):
    """Una instancia de cada servicio, y dos réplicas del catálogo."""
    for name, ip in [
        ("users-playlists", "10.0.1.1"),
        ("playback-metrics", "10.0.2.1"),
        ("web", "10.0.3.1"),
        ("catalog-streaming", "10.0.4.1"),
        ("catalog-streaming", "10.0.4.2"),
    ]:
        consul.add(name, f"{name}-{ip}", ip)
        network.add(ip, f"{name}@{ip}")
    return consul, network


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
