import os
import re
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import HTTPException, Response, status
from fastapi.responses import StreamingResponse

RANGE_REGEX = re.compile(r"bytes=(\d*)-(\d*)")
BUFFER_SIZE = 64 * 1024  # 64 KB por lectura asíncrona


async def send_bytes_range(
    file_path: Path, start: int, end: int, chunk_size: int = BUFFER_SIZE
) -> AsyncGenerator[bytes, None]:
    """Lee y emite fragmentos de archivo de forma asíncrona dentro del rango solicitado."""
    with open(file_path, "rb") as f:
        f.seek(start)
        bytes_to_read = (end - start) + 1
        while bytes_to_read > 0:
            read_now = min(bytes_to_read, chunk_size)
            data = f.read(read_now)
            if not data:
                break
            bytes_to_read -= len(data)
            yield data


def handle_range_streaming(
    file_path_str: str,
    range_header: str | None,
    mime_type: str = "audio/wav",
) -> Response:
    """Procesa una solicitud de streaming de audio soportando HTTP Range Requests (RFC 7233)."""
    file_path = Path(file_path_str)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo de audio no se encuentra en el servidor de almacenamiento.",
        )

    file_size = os.path.getsize(file_path)

    # 1. Sin cabecera Range: se sirve el archivo completo con soporte anunciado de Range
    if not range_header:
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": mime_type,
        }
        return StreamingResponse(
            send_bytes_range(file_path, 0, file_size - 1),
            status_code=status.HTTP_200_OK,
            headers=headers,
        )

    # 2. Con cabecera Range: procesar sintaxis bytes=start-end
    match = RANGE_REGEX.match(range_header.strip())
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cabecera Range inválida. Debe tener el formato 'bytes=start-end'.",
        )

    start_str, end_str = match.groups()

    if start_str and end_str:
        start = int(start_str)
        end = int(end_str)
    elif start_str and not end_str:
        start = int(start_str)
        end = file_size - 1
    elif not start_str and end_str:
        # Sufijo: los últimos N bytes
        suffix_length = int(end_str)
        start = max(0, file_size - suffix_length)
        end = file_size - 1
    else:
        start = 0
        end = file_size - 1

    # Validaciones de límites del rango
    if start >= file_size or start > end:
        headers = {
            "Content-Range": f"bytes */{file_size}",
            "Accept-Ranges": "bytes",
        }
        raise HTTPException(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            detail="El rango solicitado está fuera de los límites del archivo.",
            headers=headers,
        )

    # Ajustar límite superior si excede el tamaño del archivo
    end = min(end, file_size - 1)
    content_length = (end - start) + 1

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
    }

    return StreamingResponse(
        send_bytes_range(file_path, start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )
