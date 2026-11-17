"""Lectura de metadatos para playlists. Compose configura siempre el transporte HTTP."""
import asyncio
from uuid import UUID

import httpx

from app.core.breaker import CircuitBreaker
from app.core.catalog_contract import BATCH_LIMIT, BATCH_PATH, SongBatchRequest, SongBatchResponse, SongSummary
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.internal import internal_client


_breaker = CircuitBreaker()


def unavailable():
    return AppError(503, "catalog_unavailable", "El catálogo no responde")


async def fetch_batch(client, url, headers, batch):
    with _breaker.request(unavailable):
        for delay in (0, 0.2, 0.4):
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.post(url, headers=headers, json=batch.model_dump(mode="json"))
                if response.status_code < 500:
                    break
                response.raise_for_status()
            except httpx.HTTPError as error:
                if delay == 0.4:
                    raise unavailable() from error
    try:
        response.raise_for_status()
        return SongBatchResponse.model_validate_json(response.content)
    except (httpx.HTTPError, ValueError) as error:
        raise unavailable() from error


async def get_songs(ids: list[UUID]) -> dict[UUID, SongSummary]:
    if not ids:
        return {}
    settings = get_settings()
    if not settings.CATALOG_SERVICE_URL:
        # Compatibilidad con el arranque del monolito fuera de Compose.
        from app.modules.catalog.public import get_songs as local_songs

        return await local_songs(ids)

    songs = {}
    headers = {"X-Catalog-Token": settings.CATALOG_INTERNAL_TOKEN.get_secret_value()}
    async with internal_client() as client:
        for start in range(0, len(ids), BATCH_LIMIT):
            batch = SongBatchRequest(ids=ids[start:start + BATCH_LIMIT])
            result = await fetch_batch(client, settings.CATALOG_SERVICE_URL.rstrip("/") + BATCH_PATH, headers, batch)
            songs.update((song.id, song) for song in result.songs)
    return songs
