"""Cliente HTTP para llamadas entre servicios: 3 s de espera y sin reintentos."""
from typing import Any
from uuid import UUID

import httpx

from meloxo_common.errors import AppError

BATCH_SIZE = 200


class UpstreamError(AppError):
    def __init__(self, message: str = "Un servicio interno no responde", detail: object | None = None):
        super().__init__(503, "upstream_unavailable", message, detail)


class InternalClient:
    def __init__(self, base_url: str, timeout: float = 3.0):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **params: Any) -> Any:
        return await self._request("GET", path, params=params or None)

    async def post(self, path: str, json: Any = None) -> Any:
        return await self._request("POST", path, json=json)

    async def get_ids(self, path: str, ids: list[UUID], key: str = "ids") -> list[Any]:
        """Pide `ids` en lotes de 200 y une las listas que devuelve cada llamada."""
        result: list[Any] = []
        for start in range(0, len(ids), BATCH_SIZE):
            batch = ",".join(str(i) for i in ids[start : start + BATCH_SIZE])
            result.extend(await self.get(path, **{key: batch}))
        return result

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise UpstreamError(detail=type(exc).__name__) from exc
        if response.status_code >= 500:
            raise UpstreamError(detail=response.status_code)
        if response.status_code >= 400:
            raise _app_error(response)
        return response.json() if response.content else None


def _app_error(response: httpx.Response) -> AppError:
    try:
        error = response.json()["error"]
        return AppError(response.status_code, error["code"], error["message"], error.get("detail"))
    except (ValueError, KeyError, TypeError):
        return AppError(response.status_code, "http_error", response.reason_phrase)
