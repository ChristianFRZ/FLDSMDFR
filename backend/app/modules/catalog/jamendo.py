"""Cliente de la API de Jamendo y mapeo a las columnas del catálogo."""
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

MAX_PAGE = 200
TIMEOUT = 10.0
_LICENSE = re.compile(r"/licenses/([a-z-]+)/([\d.]+)")


class JamendoError(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


def license_name(url: str | None) -> str:
    match = _LICENSE.search(url or "")
    return f"CC {match[1].upper()} {match[2]}" if match else "Licencia de Jamendo"


@dataclass(frozen=True)
class JamendoTrack:
    jamendo_id: str
    title: str
    duration: float
    artist_id: str
    artist_name: str
    album_id: str | None
    album_name: str | None
    genres: list[str]
    tags: list[str]
    cover_url: str | None
    audio_url: str | None
    share_url: str | None
    license: str
    license_url: str | None


def to_track(raw: dict) -> JamendoTrack:
    tags = (raw.get("musicinfo") or {}).get("tags") or {}
    return JamendoTrack(
        jamendo_id=str(raw["id"]),
        title=raw.get("name") or "Sin título",
        duration=float(raw.get("duration") or 0),
        artist_id=str(raw.get("artist_id") or ""),
        artist_name=raw.get("artist_name") or "Desconocido",
        album_id=str(raw["album_id"]) if raw.get("album_id") else None,
        album_name=raw.get("album_name") or None,
        genres=list(tags.get("genres") or []),
        tags=list(tags.get("vartags") or []),
        cover_url=raw.get("image") or raw.get("album_image") or None,
        audio_url=raw.get("audio") or None,
        share_url=raw.get("shareurl") or None,
        license=license_name(raw.get("license_ccurl")),
        license_url=raw.get("license_ccurl") or None,
    )


class JamendoClient:
    async def ping(self) -> None:
        await self._get({"limit": 1})

    async def _get(self, params: dict) -> list[JamendoTrack]:
        settings = get_settings()
        query = {
            "client_id": settings.JAMENDO_CLIENT_ID,
            "format": "json",
            "include": "musicinfo licenses",
            "audioformat": "mp32",
            **params,
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(f"{settings.JAMENDO_API_URL}/tracks/", params=query)
        except httpx.HTTPError as exc:
            raise JamendoError(f"No se pudo contactar a Jamendo: {exc}") from exc
        if response.status_code != 200:
            raise JamendoError(f"Jamendo respondió {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise JamendoError("Jamendo no respondió con JSON") from exc
        headers = body.get("headers") or {}
        if headers.get("status") != "success":
            raise JamendoError(f"Jamendo rechazó la petición: {headers.get('error_message')}", retryable=False)
        return [to_track(raw) for raw in body.get("results") or []]

    async def fetch_tracks(self, genre: str | None, limit: int, offset: int, order: str) -> list[JamendoTrack]:
        params = {"limit": min(limit, MAX_PAGE), "offset": offset, "order": order}
        if genre:
            params["tags"] = genre
        return await self._get(params)

    async def fetch_by_ids(self, ids: list[str]) -> list[JamendoTrack]:
        return await self._get({"id": " ".join(ids), "limit": min(len(ids), MAX_PAGE)})
