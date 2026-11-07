"""Validación y guardado de archivos subidos. El nombre en disco siempre es un UUID."""
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from mutagen import MutagenError
from mutagen.mp3 import MP3

from app.core.config import get_settings
from app.core.errors import AppError

CHUNK = 1024 * 1024
JPG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def media_root() -> Path:
    return Path(get_settings().MEDIA_DIR)


def _invalid_audio() -> AppError:
    return AppError(422, "invalid_audio", "El archivo no es un MP3 válido")


def validate_mp3(path: Path) -> float:
    """Comprueba el contenido real del archivo y devuelve su duración en segundos."""
    with path.open("rb") as file:
        head = file.read(3)
    is_sync = len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0
    if head != b"ID3" and not is_sync:
        raise _invalid_audio()
    try:
        info = MP3(path).info
    except (MutagenError, OSError) as exc:
        raise _invalid_audio() from exc
    if not info.length or info.length <= 0:
        raise _invalid_audio()
    limit = get_settings().UPLOAD_MAX_MINUTES * 60
    if info.length > limit:
        raise AppError(422, "audio_too_long", f"La pista dura más de {get_settings().UPLOAD_MAX_MINUTES} minutos")
    return float(info.length)


def validate_cover(path: Path) -> str:
    with path.open("rb") as file:
        head = file.read(8)
    if head.startswith(JPG_MAGIC):
        return "jpg"
    if head.startswith(PNG_MAGIC):
        return "png"
    raise AppError(422, "invalid_cover", "La portada debe ser JPG o PNG")


async def _save_temp(upload: UploadFile, max_bytes: int, too_large: AppError) -> Path:
    folder = media_root() / "tmp"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid4()}.part"
    written = 0
    try:
        with path.open("wb") as out:
            while chunk := await upload.read(CHUNK):
                written += len(chunk)
                if written > max_bytes:
                    raise too_large
                out.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def _move(temp: Path, folder: str, extension: str) -> str:
    target = media_root() / folder
    target.mkdir(parents=True, exist_ok=True)
    name = f"{folder}/{uuid4()}.{extension}"
    temp.replace(media_root() / name)
    return name


async def store_audio(upload: UploadFile) -> tuple[str, float]:
    limit = get_settings().UPLOAD_MAX_MP3_MB
    too_large = AppError(413, "audio_too_large", f"El MP3 supera {limit} MB")
    temp = await _save_temp(upload, limit * 1024 * 1024, too_large)
    try:
        duration = validate_mp3(temp)
        return _move(temp, "audio", "mp3"), duration
    finally:
        temp.unlink(missing_ok=True)


async def store_cover(upload: UploadFile) -> str:
    limit = get_settings().UPLOAD_MAX_COVER_MB
    too_large = AppError(413, "cover_too_large", f"La portada supera {limit} MB")
    temp = await _save_temp(upload, limit * 1024 * 1024, too_large)
    try:
        return _move(temp, "covers", validate_cover(temp))
    finally:
        temp.unlink(missing_ok=True)


def delete_media(*names: str | None) -> None:
    for name in names:
        if name:
            (media_root() / name).unlink(missing_ok=True)


def resolve_cover(path: str) -> Path | None:
    """Solo se sirven portadas, y nunca fuera de su carpeta."""
    root = (media_root() / "covers").resolve()
    candidate = (media_root() / path).resolve()
    return candidate if candidate.is_relative_to(root) and candidate.is_file() else None
