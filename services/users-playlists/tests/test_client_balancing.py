"""Los clientes internos piden instancias al directorio y reparten en round-robin."""

import uuid

import httpx
import pytest

from app.clients import catalog, http
from app.shared import discovery
from tests.fake_catalog import FakeCatalog
from tests.fake_consul import FakeConsul


class _ByHost(httpx.AsyncBaseTransport):
    """La "red": cada IP registrada en el directorio es un catálogo falso distinto."""

    def __init__(self, apps: dict[str, FakeCatalog]):
        self.transports = {h: httpx.ASGITransport(app=c.app) for h, c in apps.items()}
        self.hits: list[str] = []

    async def handle_async_request(self, request):
        self.hits.append(request.url.host)
        return await self.transports[request.url.host].handle_async_request(request)


@pytest.fixture
def directory():
    consul = FakeConsul()
    discovery.set_consul_transport(httpx.ASGITransport(app=consul.app))
    discovery.reset()
    http.set_transport("catalog-streaming", None)  # usar el directorio, no el atajo de pruebas
    yield consul
    discovery.reset()
    discovery.set_consul_transport(None)
    http.set_network_transport(None)


async def test_client_balances_between_instances(directory):
    a, b = FakeCatalog(), FakeCatalog()
    directory.add("catalog-streaming", "catalog-streaming-a", "10.0.0.1")
    directory.add("catalog-streaming", "catalog-streaming-b", "10.0.0.2")
    network = _ByHost({"10.0.0.1": a, "10.0.0.2": b})
    http.set_network_transport(network)

    for _ in range(4):
        await catalog.get_songs_by_ids([uuid.uuid4()])

    assert network.hits == ["10.0.0.1", "10.0.0.2", "10.0.0.1", "10.0.0.2"]


async def test_no_instances_is_503(directory):
    with pytest.raises(http.RemoteUnavailable) as exc:
        await catalog.get_song(uuid.uuid4())
    assert exc.value.service == "catalog-streaming"
