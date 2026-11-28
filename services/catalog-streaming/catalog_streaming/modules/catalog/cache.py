"""Caché de lectura del catálogo: se invalida subiendo una versión que va dentro de la clave."""
from meloxo_common import cache

NAMESPACE = "catalog"
TTL_SECONDS = 300


async def cached(route: str, params: dict, loader):
    """Lee `route` con sus parámetros de la caché versionada del catálogo."""
    return await cache.cached(NAMESPACE, {"route": route, **params}, TTL_SECONDS, loader, versioned=True)


async def invalidate() -> None:
    """Llamar después del commit de toda escritura que cambie lo que devuelven las lecturas cacheadas."""
    await cache.bump(NAMESPACE)
