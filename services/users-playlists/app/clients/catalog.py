"""Cliente de catalog-streaming. Conserva los nombres y tipos que este servicio usaba cuando
el catálogo era un módulo del monolito, pero sin `session`: ahora es una llamada de red."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from app.clients import http
from app.clients.catalog_schemas import SongOut
from app.config import get_settings

SERVICE = "catalog-streaming"


async def _call(method: str, path: str, **kwargs):
    base_url = get_settings().catalog_url
    return await http.call(SERVICE, base_url, method, f"/internal{path}", **kwargs)


def normalize_artist(name: str) -> str:
    """Copia de la regla del catálogo (strip + minúsculas) para las claves de seguimiento."""
    return name.strip().lower()


async def get_song(song_id: uuid.UUID) -> SongOut:
    """404 `song_not_found` si no existe o está inactiva."""
    return SongOut.model_validate((await _call("GET", f"/songs/{song_id}")).json())


async def get_songs_by_ids(ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, SongOut]:
    """Incluye canciones inactivas (con `is_active=False`)."""
    if not ids:
        return {}
    body = (await _call("POST", "/songs/batch", json={"ids": [str(i) for i in ids]})).json()
    songs = [SongOut.model_validate(s) for s in body]
    return {s.id: s for s in songs}


async def find_song_by_title_artist(title: str, artist: str) -> SongOut | None:
    try:
        response = await _call("GET", "/songs/lookup", params={"title": title, "artist": artist})
    except http.NotFound:
        return None
    return SongOut.model_validate(response.json())


async def count_active_by_artists(artists: Sequence[str]) -> dict[str, int]:
    if not artists:
        return {}
    return (await _call("POST", "/artists/counts", json={"artists": list(artists)})).json()


async def latest_song_by_artists(artists: Sequence[str]) -> dict[str, SongOut]:
    if not artists:
        return {}
    body = (await _call("POST", "/artists/latest", json={"artists": list(artists)})).json()
    return {k: SongOut.model_validate(v) for k, v in body.items()}


async def songs_by_artists_since(
    follows: Sequence[tuple[str, datetime]], not_before: datetime
) -> list[SongOut]:
    if not follows:
        return []
    payload = {
        "follows": [{"artist": a, "since": since.isoformat()} for a, since in follows],
        "not_before": not_before.isoformat(),
    }
    body = (await _call("POST", "/artists/releases", json=payload)).json()
    return [SongOut.model_validate(s) for s in body]
