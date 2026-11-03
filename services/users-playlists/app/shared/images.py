"""Portadas subidas: validación por bytes mágicos, límite de tamaño y guardado atómico."""

import uuid
from pathlib import Path

import anyio
from fastapi import UploadFile
from fastapi.responses import FileResponse, Response

from app.shared.errors import InvalidInput, PayloadTooLarge

IMAGE_MAX_BYTES = 2_097_152
_CHUNK = 64 * 1024
_MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def _detect(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def image_media_type(filename: str) -> str:
    return _MEDIA_TYPES[Path(filename).suffix.lstrip(".").lower()]


async def save_image(upload: UploadFile, dest_dir: Path, stem: str) -> str:
    """Guarda la imagen como `<stem>.<ext>` y borra versiones previas con otra extensión.

    Si la imagen no es válida, la portada anterior se conserva intacta.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest_dir / f".tmp-{uuid.uuid4().hex}"
    try:
        written = 0
        head = b""
        async with await anyio.open_file(tmp, "wb") as out:
            while chunk := await upload.read(_CHUNK):
                if len(head) < 12:
                    head += chunk[: 12 - len(head)]
                written += len(chunk)
                if written > IMAGE_MAX_BYTES:
                    raise PayloadTooLarge("La imagen pesa más de 2 MB.", code="image_too_large")
                await out.write(chunk)
        ext = _detect(head)
        if ext is None:
            raise InvalidInput(
                "La portada debe ser una imagen PNG, JPEG o WebP.", code="invalid_image"
            )
        name = f"{stem}.{ext}"
        tmp.replace(dest_dir / name)
    finally:
        tmp.unlink(missing_ok=True)
    for old in dest_dir.glob(f"{stem}.*"):
        if old.name != name:
            old.unlink(missing_ok=True)
    return name


def delete_image(dest_dir: Path, filename: str | None) -> None:
    if filename:
        (dest_dir / filename).unlink(missing_ok=True)


def image_response(path: Path, if_none_match: str | None) -> Response:
    stat = path.stat()
    etag = f'"{stat.st_mtime_ns}-{stat.st_size}"'
    headers = {"ETag": etag, "Cache-Control": "private, max-age=86400"}
    if if_none_match and etag in [t.strip() for t in if_none_match.split(",")]:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=image_media_type(path.name), headers=headers)
