"""Timeout por intento, un reintento en otra instancia y circuit breaker en http.call."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.clients import http
from app.config import get_settings
from app.shared import discovery
from tests.fake_consul import FakeConsul

SERVICE = "catalog-streaming"


class Remote:
    """Una instancia falsa: cuenta las llamadas y se comporta según `mode`."""

    def __init__(self, label: str, mode: str = "ok"):
        self.label, self.mode, self.calls = label, mode, 0
        self.app = FastAPI()

        @self.app.get("/internal/ping")
        async def ping():
            self.calls += 1
            if self.mode == "slow":
                await asyncio.sleep(1)
            if self.mode == "500":
                return JSONResponse({"error": {"code": "boom", "message": "x"}}, status_code=500)
            if self.mode == "400":
                return JSONResponse({"error": {"code": "bad", "message": "x"}}, status_code=400)
            return {"label": self.label}


class Network(httpx.AsyncBaseTransport):
    def __init__(self, remotes: dict[str, Remote]):
        self.remotes = remotes
        self.transports = {h: httpx.ASGITransport(app=r.app) for h, r in remotes.items()}

    async def handle_async_request(self, request):
        return await self.transports[request.url.host].handle_async_request(request)


@pytest.fixture
def directory(monkeypatch):
    consul = FakeConsul()
    discovery.set_consul_transport(httpx.ASGITransport(app=consul.app))
    discovery.reset()
    http.set_transport(SERVICE, None)
    http.reset_breakers()
    monkeypatch.setattr(get_settings(), "call_timeout_s", 0.1)
    monkeypatch.setattr(http, "retry_wait", lambda: 0)
    yield consul
    discovery.reset()
    discovery.set_consul_transport(None)
    http.set_network_transport(None)
    http.reset_breakers()


def _two(directory, mode_a: str, mode_b: str = "ok") -> tuple[Remote, Remote]:
    a, b = Remote("a", mode_a), Remote("b", mode_b)
    directory.add(SERVICE, f"{SERVICE}-a", "10.0.0.1")
    directory.add(SERVICE, f"{SERVICE}-b", "10.0.0.2")
    http.set_network_transport(Network({"10.0.0.1": a, "10.0.0.2": b}))
    return a, b


async def _ping() -> httpx.Response:
    return await http.call(SERVICE, "GET", "/internal/ping")


def _breaker() -> dict:
    return next(b.snapshot() for b in http.breakers() if b.target == SERVICE)


async def test_timeout_retries_other_instance(directory):
    a, b = _two(directory, "slow")
    r = await _ping()
    assert r.json()["label"] == "b"
    assert (a.calls, b.calls) == (1, 1)
    assert _breaker()["consecutive_failures"] == 0


async def test_5xx_retried_and_counted_once(directory):
    a, b = _two(directory, "500", "500")
    with pytest.raises(http.RemoteUnavailable):
        await _ping()
    assert a.calls + b.calls == 2
    assert _breaker()["consecutive_failures"] == 1


async def test_4xx_not_retried_not_counted(directory):
    a, b = _two(directory, "400", "400")
    with pytest.raises(http.RemoteUnavailable):
        await _ping()
    assert a.calls + b.calls == 1
    assert _breaker()["consecutive_failures"] == 0


async def test_opens_after_five_failed_calls(directory):
    _two(directory, "500", "500")
    for _ in range(5):
        with pytest.raises(http.RemoteUnavailable):
            await _ping()
    assert _breaker()["state"] == "open"


async def test_open_circuit_does_not_call(directory):
    a, b = _two(directory, "500", "500")
    for _ in range(5):
        with pytest.raises(http.RemoteUnavailable):
            await _ping()
    before = a.calls + b.calls
    with pytest.raises(http.RemoteUnavailable) as exc:
        await _ping()
    assert exc.value.service == SERVICE
    assert a.calls + b.calls == before


async def test_no_instances_counts_as_failure(directory):
    with pytest.raises(http.RemoteUnavailable):
        await _ping()
    assert _breaker()["consecutive_failures"] == 1
