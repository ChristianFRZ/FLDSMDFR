import re
from collections.abc import AsyncIterator
from pathlib import Path

import anyio
from fastapi import Response
from fastapi.responses import StreamingResponse

from app.shared.errors import RangeNotSatisfiable, error_response

_CHUNK_SIZE = 64 * 1024
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Interpreta `Range` (rango inclusivo). `None` indica servir el archivo completo.

    Multirango, unidades distintas de bytes o sintaxis inválida se ignoran (200 completo).
    Un rango fuera del archivo lanza `RangeNotSatisfiable`.
    """
    if not header:
        return None
    match = _RANGE_RE.match(header.strip())
    if match is None:
        return None
    first, last = match.groups()
    unsatisfiable = RangeNotSatisfiable("El rango pedido no está dentro del archivo.", size=size)
    if first == "" and last == "":
        return None
    if first == "":
        suffix = int(last)
        if suffix == 0 or size == 0:
            raise unsatisfiable
        return max(size - suffix, 0), size - 1
    start = int(first)
    end = size - 1 if last == "" else min(int(last), size - 1)
    if start >= size or start > end:
        raise unsatisfiable
    return start, end


async def _iter_file(path: Path, start: int, end: int) -> AsyncIterator[bytes]:
    remaining = end - start + 1
    async with await anyio.open_file(path, "rb") as file:
        await file.seek(start)
        while remaining > 0:
            chunk = await file.read(min(_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


async def file_response(
    path: Path, mime_type: str, size: int, range_header: str | None
) -> Response:
    try:
        byte_range = parse_range(range_header, size)
    except RangeNotSatisfiable as exc:
        return error_response(
            exc.status, exc.code, exc.message, headers={"Content-Range": f"bytes */{size}"}
        )
    headers = {"Accept-Ranges": "bytes"}
    if byte_range is None:
        start, end, status = 0, size - 1, 200
    else:
        start, end = byte_range
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    headers["Content-Length"] = str(end - start + 1)
    return StreamingResponse(
        _iter_file(path, start, end), status_code=status, media_type=mime_type, headers=headers
    )
