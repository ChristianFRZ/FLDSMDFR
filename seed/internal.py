"""Clientes HTTP de las rutas `/internal/demo/*` de los tres servicios."""
import dataclasses
import json
import os
from datetime import datetime
from uuid import UUID

import httpx

# La importación de Jamendo y los envíos masivos tardan minutos: no vale el límite de 3 s entre servicios.
TIMEOUT = httpx.Timeout(900.0, connect=10.0)


class SeedError(RuntimeError):
    """Un servicio no respondió o contestó con error."""


def _default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    raise TypeError(f"No se puede serializar {type(value).__name__}")


def _reason(response: httpx.Response) -> str:
    try:
        error = response.json()["error"]
        return f"{error['code']}: {error['message']}"
    except (ValueError, KeyError, TypeError):
        return response.text[:200] or response.reason_phrase


class Service:
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url.rstrip("/")

    async def request(self, method: str, path: str, body=None, params=None):
        content = None if body is None else json.dumps(body, default=_default)
        headers = {"content-type": "application/json"} if content is not None else None
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.request(
                    method, f"{self.base_url}/internal/demo{path}", content=content, headers=headers, params=params
                )
        except httpx.TransportError as exc:
            raise SeedError(f"{self.name} no responde en {self.base_url}: {exc or type(exc).__name__}") from exc
        if response.is_error:
            raise SeedError(f"{self.name} {method} {path} respondió {response.status_code} {_reason(response)}")
        return response.json() if response.content else None

    async def get(self, path: str, **params):
        return await self.request("GET", path, params=params)

    async def post(self, path: str, body=None):
        return await self.request("POST", path, body)


def users() -> Service:
    return Service("users-playlists", os.environ.get("USERS_URL", "http://users-playlists:8001"))


def catalog() -> Service:
    return Service("catalog-streaming", os.environ.get("CATALOG_URL", "http://catalog-streaming:8002"))


def playback() -> Service:
    return Service("playback-metrics", os.environ.get("PLAYBACK_URL", "http://playback-metrics:8003"))
