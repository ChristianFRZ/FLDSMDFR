"""Contratos internos tipados. Solo las operaciones decoradas tienen una ruta privada."""
from contextlib import asynccontextmanager
from functools import wraps
from inspect import Parameter, signature
from secrets import compare_digest

import httpx
from fastapi import APIRouter, Depends, Header
from pydantic import TypeAdapter, create_model

from app.core.config import get_settings
from app.core.errors import AppError

HOSTS = {
    "users": "http://users-playlists-service:8080",
    "catalog": "http://catalog-streaming-service:8080",
    "playback": "http://playback-metrics-service:8080",
}


_pool: httpx.AsyncClient | None = None


@asynccontextmanager
async def transport_lifespan():
    global _pool
    async with httpx.AsyncClient(trust_env=False, timeout=get_settings().CATALOG_TIMEOUT_SECONDS) as client:
        _pool = client
        try:
            yield
        finally:
            _pool = None


@asynccontextmanager
async def internal_client():
    if _pool is not None:
        yield _pool
    else:
        async with httpx.AsyncClient(trust_env=False, timeout=get_settings().CATALOG_TIMEOUT_SECONDS) as client:
            yield client


def require_internal_token(x_catalog_token: str = Header(default="")) -> None:
    token = get_settings().CATALOG_INTERNAL_TOKEN.get_secret_value()
    if not token or not compare_digest(x_catalog_token.encode(), token.encode()):
        raise AppError(403, "forbidden", "Credencial interna no válida")


routers = {name: APIRouter(dependencies=[Depends(require_internal_token)]) for name in HOSTS}


def internal(owner: str):
    """La firma pública define el JSON de entrada y salida para cliente y servidor."""
    def register(function):
        spec = signature(function)
        fields = {p.name: (p.annotation, ... if p.default is Parameter.empty else p.default)
                  for p in spec.parameters.values()}
        request_type = create_model(function.__name__ + "_request", **fields)
        response_type = TypeAdapter(spec.return_annotation)
        path = "/internal/" + function.__name__

        async def endpoint(body: request_type):
            return await function(**{key: getattr(body, key) for key in fields})

        routers[owner].add_api_route(path, endpoint, methods=["POST"], response_model=spec.return_annotation)

        @wraps(function)
        async def call(*args, **kwargs):
            settings = get_settings()
            if settings.SERVICE_NAME in ("monolith", owner):
                return await function(*args, **kwargs)
            body = request_type(**spec.bind(*args, **kwargs).arguments)
            headers = {"X-Catalog-Token": settings.CATALOG_INTERNAL_TOKEN.get_secret_value()}
            try:
                async with internal_client() as client:
                    response = await client.post(HOSTS[owner] + path, headers=headers, json=body.model_dump(mode="json"))
                    response.raise_for_status()
                return response_type.validate_json(response.content)
            except (httpx.HTTPError, ValueError) as error:
                raise AppError(503, "service_unavailable", f"Servicio no disponible: {owner}") from error

        return call
    return register
