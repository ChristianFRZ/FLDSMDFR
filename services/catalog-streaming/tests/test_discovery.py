"""Registro en el directorio (Consul) con latido, baja, consulta con caché y round-robin."""

import socket

import httpx
import pytest

from app.shared import discovery
from tests.fake_consul import FakeConsul


@pytest.fixture
def consul() -> FakeConsul:
    fake = FakeConsul()
    discovery.set_consul_transport(httpx.ASGITransport(app=fake.app))
    discovery.reset()
    yield fake
    discovery.reset()
    discovery.set_consul_transport(None)


class _Down(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request):
        raise httpx.ConnectError("directorio caído", request=request)


async def test_register_sends_ttl_check(consul):
    instance = await discovery.register("catalog-streaming", 8000, start_heartbeat=False)
    assert instance == f"catalog-streaming-{socket.gethostname()}"
    body = consul.services[instance]
    assert body["Name"] == "catalog-streaming"
    assert body["Port"] == 8000
    assert body["Check"]["TTL"] == "10s"
    assert body["Check"]["DeregisterCriticalServiceAfter"] == "1m"


async def test_heartbeat_passes_check(consul):
    instance = await discovery.register("catalog-streaming", 8000, start_heartbeat=False)
    # El registro manda el primer latido: la instancia nace viva.
    assert len(await discovery.instances("catalog-streaming", use_cache=False)) == 1
    consul.kill(instance)  # venció el TTL
    assert await discovery.instances("catalog-streaming", use_cache=False) == []
    await discovery.heartbeat_once()
    assert len(await discovery.instances("catalog-streaming", use_cache=False)) == 1


async def test_deregister_removes_instance(consul):
    instance = await discovery.register("catalog-streaming", 8000, start_heartbeat=False)
    await discovery.deregister()
    assert instance not in consul.services


async def test_instances_only_passing_and_cached(consul):
    consul.add("catalog-streaming", "c-1", "10.0.0.1")
    consul.add("catalog-streaming", "c-2", "10.0.0.2")
    consul.kill("c-2")
    assert await discovery.instances("catalog-streaming") == ["http://10.0.0.1:8000"]
    consul.add("catalog-streaming", "c-3", "10.0.0.3")
    # La caché del balanceador todavía no ve la instancia nueva.
    assert await discovery.instances("catalog-streaming") == ["http://10.0.0.1:8000"]


async def test_round_robin_cycles(consul):
    consul.add("catalog-streaming", "c-1", "10.0.0.1")
    consul.add("catalog-streaming", "c-2", "10.0.0.2")
    rr = discovery.RoundRobin()
    picks = [await rr.pick("catalog-streaming") for _ in range(4)]
    assert picks == ["http://10.0.0.1:8000", "http://10.0.0.2:8000"] * 2


async def test_no_instances_raises(consul):
    with pytest.raises(discovery.NoInstances):
        await discovery.RoundRobin().pick("catalog-streaming")


async def test_directory_down_means_no_instances(consul):
    discovery.set_consul_transport(_Down())
    with pytest.raises(discovery.NoInstances):
        await discovery.RoundRobin().pick("catalog-streaming")


async def test_register_retries_when_directory_down(consul):
    discovery.set_consul_transport(_Down())
    instance = await discovery.register("catalog-streaming", 8000, start_heartbeat=False)
    assert instance not in consul.services  # no se pudo registrar, pero no truena
    discovery.set_consul_transport(httpx.ASGITransport(app=consul.app))
    await discovery.heartbeat_once()  # el latido descubre que no existe y se registra
    await discovery.heartbeat_once()
    assert consul.status[f"{instance}-ttl"] == "passing"


async def test_responses_carry_x_instancia(client):
    r = await client.get("/api/health")
    assert r.headers["X-Instancia"] == f"catalog-streaming-{socket.gethostname()}"


async def test_heartbeat_reregisters_when_address_changes(consul, monkeypatch):
    """Si Docker le cambia la IP a un contenedor vivo, el latido corrige el registro: si no, el
    directorio anunciaría una IP que ahora es de otro servicio."""
    monkeypatch.setattr(discovery, "_address", lambda: "10.0.0.1")
    instance = await discovery.register("catalog-streaming", 8000, start_heartbeat=False)
    monkeypatch.setattr(discovery, "_address", lambda: "10.0.0.2")
    await discovery.heartbeat_once()
    assert consul.services[instance]["Address"] == "10.0.0.2"
    assert await discovery.instances("catalog-streaming", use_cache=False) == [
        "http://10.0.0.2:8000"
    ]
