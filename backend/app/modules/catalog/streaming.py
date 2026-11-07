"""Entrega de audio con Range: archivo local o proxy hacia Jamendo, sin escribir a disco."""
import re
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import UUID

import anyio
import httpx
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from sqlalchemy import update

from app.core.config import get_settings
from app.core.db import session_scope
from app.core.errors import AppError
from app.modules.catalog.jamendo import JamendoClient, JamendoError
from app.modules.catalog.models import Song

CHUNK = 64 * 1024
JAMENDO_TIMEOUT = 3.0
MAX_RANGE_DIGITS = 18
JAMENDO_ATTEMPTS = 2
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
_FORWARDED = ("content-type", "content-length", "content-range", "accept-ranges")


def _not_satisfiable(size: int) -> AppError:
    return AppError(416, "range_not_satisfiable", "Rango no válido", {"size": size})


def _position(digits: str) -> int:
    """int() rechaza textos de miles de dígitos. Un número así queda más allá de cualquier archivo."""
    return sys.maxsize if len(digits) > MAX_RANGE_DIGITS else int(digits)


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    if header is None:
        return None
    match = _RANGE.match(header.strip())
    if match is None or not (match[1] or match[2]):
        raise _not_satisfiable(size)
    if not match[1]:
        suffix = _position(match[2])
        if suffix == 0:
            raise _not_satisfiable(size)
        return max(size - suffix, 0), size - 1
    start = _position(match[1])
    end = _position(match[2]) if match[2] else size - 1
    if start >= size or end < start:
        raise _not_satisfiable(size)
    return start, min(end, size - 1)


@dataclass(frozen=True)
class StreamTarget:
    source: str
    audio_path: str | None
    audio_url: str | None
    jamendo_id: str | None = None


async def load_target(song_id: UUID) -> StreamTarget:
    """Carga lo necesario y libera la conexión a la base antes de empezar a transmitir."""
    async with session_scope() as session:
        song = await session.get(Song, song_id)
        if song is None or song.status != "published":
            raise AppError(404, "song_not_found", "Canción no encontrada")
        return StreamTarget(song.source, song.audio_path, song.audio_url, song.jamendo_id)


async def _read_file(path: Path, start: int, end: int) -> AsyncIterator[bytes]:
    remaining = end - start + 1
    async with await anyio.open_file(path, "rb") as file:
        await file.seek(start)
        while remaining > 0:
            chunk = await file.read(min(CHUNK, remaining))
            if not chunk:
                return
            remaining -= len(chunk)
            yield chunk


def stream_local(audio_path: str | None, range_header: str | None) -> Response:
    path = Path(get_settings().MEDIA_DIR) / (audio_path or "")
    if not audio_path or not path.is_file():
        raise AppError(404, "audio_missing", "El audio de esta pista no está disponible")
    size = path.stat().st_size
    try:
        selected = parse_range(range_header, size)
    except AppError as exc:
        headers = {"Content-Range": f"bytes */{size}"}
        return Response(status_code=exc.status, headers=headers)
    start, end = selected or (0, size - 1)
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1)}
    if selected is not None:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    status = 206 if selected is not None else 200
    return StreamingResponse(_read_file(path, start, end), status_code=status, media_type="audio/mpeg", headers=headers)


@lru_cache
def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=JAMENDO_TIMEOUT, follow_redirects=True)


def _unavailable() -> AppError:
    return AppError(503, "jamendo_unavailable", "Jamendo no responde. Esta pista no se puede reproducir ahora.")


class _ExpiredUrl(Exception):
    pass


async def _open_upstream(url: str, range_header: str | None) -> httpx.Response:
    client = _http_client()
    request_headers = {"Range": range_header} if range_header else {}
    for attempt in range(JAMENDO_ATTEMPTS):
        try:
            response = await client.send(client.build_request("GET", url, headers=request_headers), stream=True)
        except httpx.HTTPError as exc:
            if attempt + 1 == JAMENDO_ATTEMPTS:
                raise _unavailable() from exc
            continue
        if response.status_code in (200, 206):
            return response
        await response.aclose()
        if response.status_code == 416:
            raise AppError(416, "range_not_satisfiable", "Rango no válido")
        if 400 <= response.status_code < 500:
            raise _ExpiredUrl
    raise _unavailable()


async def _fresh_audio_url(jamendo_id: str | None) -> str:
    """La URL guardada puede caducar: se pide una nueva a la API y se guarda."""
    if jamendo_id is None:
        raise _unavailable()
    try:
        tracks = await JamendoClient().fetch_by_ids([jamendo_id])
    except JamendoError as exc:
        raise _unavailable() from exc
    if not tracks or not tracks[0].audio_url:
        raise _unavailable()
    url = tracks[0].audio_url
    async with session_scope() as session:
        await session.execute(update(Song).where(Song.jamendo_id == jamendo_id).values(audio_url=url))
    return url


async def _relay(upstream: httpx.Response) -> AsyncIterator[bytes]:
    try:
        async for chunk in upstream.aiter_raw(CHUNK):
            yield chunk
    finally:
        await upstream.aclose()


async def stream_jamendo(audio_url: str | None, jamendo_id: str | None, range_header: str | None) -> Response:
    if not audio_url:
        raise AppError(404, "audio_missing", "El audio de esta pista no está disponible")
    if get_settings().JAMENDO_AUDIO_MODE == "redirect":
        return RedirectResponse(audio_url, status_code=302)
    try:
        upstream = await _open_upstream(audio_url, range_header)
    except _ExpiredUrl:
        try:
            upstream = await _open_upstream(await _fresh_audio_url(jamendo_id), range_header)
        except _ExpiredUrl as exc:
            raise _unavailable() from exc
    headers = {k: v for k, v in upstream.headers.items() if k.lower() in _FORWARDED}
    headers.setdefault("accept-ranges", "bytes")
    return StreamingResponse(_relay(upstream), status_code=upstream.status_code, headers=headers)


async def stream_song(song_id: UUID, range_header: str | None) -> Response:
    target = await load_target(song_id)
    if target.source == "jamendo":
        return await stream_jamendo(target.audio_url, target.jamendo_id, range_header)
    return stream_local(target.audio_path, range_header)
