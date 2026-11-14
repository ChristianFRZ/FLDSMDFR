from uuid import uuid4

import httpx
import pytest

from meloxo_common.errors import AppError
from meloxo_common import internal
from meloxo_common.internal import InternalClient, UpstreamError

BASE = "http://svc"


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    """Sin espera entre reintentos y sin breakers heredados de otra prueba."""
    monkeypatch.setattr(internal, "RETRY_DELAYS", (0, 0))
    internal.reset_all_breakers()
    yield
    internal.reset_all_breakers()


@pytest.fixture
async def client():
    c = InternalClient(BASE)
    yield c
    await c.aclose()


async def test_get_ids_splits_into_batches_of_200(respx_mock, client):
    ids = [uuid4() for _ in range(450)]
    route = respx_mock.get(f"{BASE}/items").mock(
        side_effect=lambda request: httpx.Response(
            200, json=[{"id": i} for i in request.url.params["ids"].split(",")]
        )
    )
    result = await client.get_ids("/items", ids)
    sizes = [len(call.request.url.params["ids"].split(",")) for call in route.calls]
    assert sizes == [200, 200, 50]
    assert [r["id"] for r in result] == [str(i) for i in ids]


async def test_get_ids_empty_makes_no_call(respx_mock, client):
    assert await client.get_ids("/items", []) == []
    assert respx_mock.calls.call_count == 0


async def test_timeout_raises_upstream_error(respx_mock, client):
    respx_mock.get(f"{BASE}/x").mock(side_effect=httpx.ReadTimeout("lento"))
    with pytest.raises(UpstreamError) as exc:
        await client.get("/x")
    assert exc.value.status == 503
    assert exc.value.code == "upstream_unavailable"


async def test_connection_error_raises_upstream_error(respx_mock, client):
    respx_mock.get(f"{BASE}/x").mock(side_effect=httpx.ConnectError("caído"))
    with pytest.raises(UpstreamError):
        await client.get("/x")


async def test_5xx_raises_upstream_error(respx_mock, client):
    respx_mock.post(f"{BASE}/x").mock(return_value=httpx.Response(500))
    with pytest.raises(UpstreamError):
        await client.post("/x", json={"a": 1})


async def test_4xx_keeps_status_and_code(respx_mock, client):
    body = {"error": {"code": "not_found", "message": "No existe", "detail": None}}
    respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(404, json=body))
    with pytest.raises(AppError) as exc:
        await client.get("/x")
    assert not isinstance(exc.value, UpstreamError)
    assert (exc.value.status, exc.value.code, exc.value.message) == (404, "not_found", "No existe")


async def test_success_returns_json_and_passes_params(respx_mock, client):
    route = respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(200, json={"ok": True}))
    assert await client.get("/x", since="2026") == {"ok": True}
    assert route.calls[0].request.url.params["since"] == "2026"


async def test_get_retries_twice_then_succeeds(respx_mock, client):
    route = respx_mock.get(f"{BASE}/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    assert await client.get("/x") == {"ok": True}
    assert route.call_count == 3


async def test_get_gives_up_after_three_attempts(respx_mock, client):
    route = respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(503))
    with pytest.raises(UpstreamError):
        await client.get("/x")
    assert route.call_count == 3


async def test_post_is_not_retried(respx_mock, client):
    route = respx_mock.post(f"{BASE}/x").mock(return_value=httpx.Response(503))
    with pytest.raises(UpstreamError):
        await client.post("/x", json={})
    assert route.call_count == 1


async def test_post_idempotent_is_retried(respx_mock, client):
    route = respx_mock.post(f"{BASE}/x").mock(side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": 1})])
    assert await client.post("/x", json={}, idempotent=True) == {"ok": 1}
    assert route.call_count == 2


async def test_4xx_is_not_retried_and_does_not_count_as_failure(respx_mock, client):
    body = {"error": {"code": "not_found", "message": "No existe", "detail": None}}
    route = respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(404, json=body))
    for _ in range(8):
        with pytest.raises(AppError):
            await client.get("/x")
    assert route.call_count == 8  # sin reintentos
    assert client.breaker.state == "closed"


async def test_retries_wait_0_2_and_0_4_seconds(respx_mock, client, monkeypatch):
    monkeypatch.undo()  # vuelve RETRY_DELAYS a sus valores reales
    internal.reset_all_breakers()
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(internal.asyncio, "sleep", fake_sleep)
    respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(503))
    with pytest.raises(UpstreamError):
        await client.get("/x")
    assert waits == [0.2, 0.4]


async def test_breaker_opens_after_five_failed_calls_and_fails_fast(respx_mock, client):
    route = respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(503))
    for _ in range(5):
        with pytest.raises(UpstreamError):
            await client.get("/x")
    calls = route.call_count
    with pytest.raises(UpstreamError) as exc:
        await client.get("/x")
    assert exc.value.detail == "circuit_open"
    assert route.call_count == calls


async def test_breaker_probe_recovers_when_service_returns(respx_mock, client):
    clock = [1000.0]
    client.breaker._clock = lambda: clock[0]
    route = respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(503))
    for _ in range(5):
        with pytest.raises(UpstreamError):
            await client.get("/x")
    route.mock(return_value=httpx.Response(200, json={"ok": True}))
    clock[0] += 15
    assert await client.get("/x") == {"ok": True}
    assert client.breaker.state == "closed"


async def test_connect_and_read_timeouts_are_separate():
    c = InternalClient(BASE)
    try:
        timeout = c._client.timeout
        assert (timeout.connect, timeout.read) == (1.0, 1.5)
    finally:
        await c.aclose()


async def test_reset_all_breakers_closes_every_client(respx_mock, client):
    respx_mock.get(f"{BASE}/x").mock(return_value=httpx.Response(503))
    for _ in range(5):
        with pytest.raises(UpstreamError):
            await client.get("/x")
    assert client.breaker.state == "open"
    internal.reset_all_breakers()
    assert client.breaker.state == "closed"
