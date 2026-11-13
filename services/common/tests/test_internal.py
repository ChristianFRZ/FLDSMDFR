from uuid import uuid4

import httpx
import pytest

from meloxo_common.errors import AppError
from meloxo_common.internal import InternalClient, UpstreamError

BASE = "http://svc"


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
