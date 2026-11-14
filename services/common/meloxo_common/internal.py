"""Cliente HTTP para llamadas entre servicios: conexión 1 s, lectura 1.5 s, reintentos con espera en lecturas y circuit breaker por destino."""
import asyncio
import weakref
from typing import Any
from uuid import UUID

import httpx

from meloxo_common.breaker import CircuitBreaker
from meloxo_common.errors import AppError

BATCH_SIZE = 200
CONNECT_TIMEOUT = 1.0
READ_TIMEOUT = 1.5
RETRY_DELAYS = (0.2, 0.4)  # espera antes del 2.º y del 3.er intento
_clients: "weakref.WeakSet[InternalClient]" = weakref.WeakSet()


def reset_all_breakers() -> None:
    """Cierra el breaker de cada cliente vivo. Lo usan las pruebas para no heredar un breaker abierto."""
    for client in _clients:
        client.breaker = CircuitBreaker()


class UpstreamError(AppError):
    def __init__(self, message: str = "Un servicio interno no responde", detail: object | None = None):
        super().__init__(503, "upstream_unavailable", message, detail)


class InternalClient:
    def __init__(self, base_url: str, timeout: float = READ_TIMEOUT):
        """`timeout` es el de lectura; el de conexión es fijo."""
        self._client = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout, connect=CONNECT_TIMEOUT))
        self.breaker = CircuitBreaker()
        _clients.add(self)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, **params: Any) -> Any:
        return await self._request("GET", path, retry=True, params=params or None)

    async def post(self, path: str, json: Any = None, idempotent: bool = False) -> Any:
        """Solo se reintenta si quien llama garantiza que repetirla no cambia el resultado."""
        return await self._request("POST", path, retry=idempotent, json=json)

    async def get_ids(self, path: str, ids: list[UUID], key: str = "ids") -> list[Any]:
        """Pide `ids` en lotes de 200 y une las listas que devuelve cada llamada."""
        result: list[Any] = []
        for start in range(0, len(ids), BATCH_SIZE):
            batch = ",".join(str(i) for i in ids[start : start + BATCH_SIZE])
            result.extend(await self.get(path, **{key: batch}))
        return result

    async def _request(self, method: str, path: str, retry: bool = False, **kwargs: Any) -> Any:
        if not self.breaker.allow():
            raise UpstreamError(detail="circuit_open")
        attempts = 1 + (len(RETRY_DELAYS) if retry else 0)
        error: UpstreamError | None = None
        for attempt in range(attempts):
            if attempt:
                await asyncio.sleep(RETRY_DELAYS[attempt - 1])
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                error = UpstreamError(detail=type(exc).__name__)
                error.__cause__ = exc
                continue
            if response.status_code >= 500:
                error = UpstreamError(detail=response.status_code)
                continue
            self.breaker.record_success()  # un 4xx es una respuesta del servicio, no una falla
            if response.status_code >= 400:
                raise _app_error(response)
            return response.json() if response.content else None
        self.breaker.record_failure()
        raise error


def _app_error(response: httpx.Response) -> AppError:
    try:
        error = response.json()["error"]
        return AppError(response.status_code, error["code"], error["message"], error.get("detail"))
    except (ValueError, KeyError, TypeError):
        return AppError(response.status_code, "http_error", response.reason_phrase)
