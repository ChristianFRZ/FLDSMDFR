import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import anyio
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.catalog import repository
from app.modules.catalog.audio import inspect_audio
from app.modules.catalog.models import Song
from app.modules.catalog.schemas import SongOut, SongPage, SongUpdate
from app.shared.errors import InvalidInput, NotFound

_NOT_FOUND = "No encontramos esa canción."
_ALLOWED_EXTENSIONS = {".mp3", ".ogg", ".wav"}
_CHUNK_SIZE = 64 * 1024


@dataclass
class StreamFile:
    path: Path
    mime_type: str
    size: int


async def list_songs(
    session: AsyncSession, q: str | None, limit: int = 50, offset: int = 0
) -> SongPage:
    songs, total = await repository.search_active(session, q.strip() if q else None, limit, offset)
    return SongPage(items=[SongOut.model_validate(s) for s in songs], total=total)


async def get_song(session: AsyncSession, song_id: uuid.UUID) -> SongOut:
    song = await repository.get_by_id(session, song_id)
    if song is None or not song.is_active:
        raise NotFound(_NOT_FOUND, code="song_not_found")
    return SongOut.model_validate(song)


async def find_song_by_title_artist(
    session: AsyncSession, title: str, artist: str
) -> SongOut | None:
    """Busca por título y artista (exacto, sin distinguir mayúsculas), incluso inactivas."""
    song = await repository.find_by_title_artist(session, title.strip(), artist.strip())
    return SongOut.model_validate(song) if song else None


async def get_songs_by_ids(
    session: AsyncSession, ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, SongOut]:
    songs = await repository.get_by_ids(session, ids)
    return {s.id: SongOut.model_validate(s) for s in songs}


async def song_is_available(session: AsyncSession, song_id: uuid.UUID) -> bool:
    song = await repository.get_by_id(session, song_id)
    return song is not None and song.is_active


async def get_stream_file(session: AsyncSession, song_id: uuid.UUID) -> StreamFile:
    song = await repository.get_by_id(session, song_id)
    if song is None or not song.is_active:
        raise NotFound(_NOT_FOUND, code="song_not_found")
    media_dir = get_settings().media_dir.resolve()
    path = (media_dir / song.file_path).resolve()
    if not path.is_relative_to(media_dir) or not path.is_file():
        raise NotFound("El archivo de audio no está disponible.", code="audio_missing")
    return StreamFile(path=path, mime_type=song.mime_type, size=path.stat().st_size)


async def count_songs(session: AsyncSession) -> int:
    return await repository.count(session)


async def _read_chunks(read, chunk_size: int = _CHUNK_SIZE) -> AsyncIterator[bytes]:
    while chunk := await read(chunk_size):
        yield chunk


async def _ingest_audio(
    session: AsyncSession,
    filename: str,
    chunks: AsyncIterator[bytes],
    title: str,
    artist: str,
    album: str,
) -> SongOut:
    """Flujo único de alta: extensión, copia acotada, validación de audio, inserción.

    Ante cualquier fallo no queda ningún archivo (temporal ni definitivo) en `media_dir`.
    """
    extension = Path(filename).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise InvalidInput("Solo se aceptan archivos .mp3, .ogg o .wav.", code="unsupported_format")
    settings = get_settings()
    media_dir = settings.media_dir
    tmp_path = media_dir / f".tmp-{uuid.uuid4().hex}{extension}"
    song_id = uuid.uuid4()
    final_path = media_dir / f"{song_id}{extension}"
    try:
        written = 0
        async with await anyio.open_file(tmp_path, "wb") as out:
            async for chunk in chunks:
                written += len(chunk)
                if written > settings.max_upload_bytes:
                    raise InvalidInput(
                        "El archivo supera el tamaño máximo permitido.", code="file_too_large"
                    )
                await out.write(chunk)
        info = await anyio.to_thread.run_sync(inspect_audio, tmp_path)
        await anyio.Path(tmp_path).rename(final_path)
        song = Song(
            id=song_id,
            title=title,
            artist=artist,
            album=album,
            duration_seconds=info.duration_seconds,
            file_path=final_path.name,
            mime_type=info.mime_type,
            size_bytes=written,
        )
        await repository.add(session, song)
        return SongOut.model_validate(song)
    except BaseException:
        try:
            await session.rollback()
        finally:
            tmp_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
        raise


async def create_song(
    session: AsyncSession, title: str, artist: str, album: str, upload: UploadFile
) -> SongOut:
    return await _ingest_audio(
        session, upload.filename or "", _read_chunks(upload.read), title, artist, album
    )


async def import_song_file(
    session: AsyncSession, source: Path, title: str, artist: str, album: str
) -> SongOut:
    async with await anyio.open_file(source, "rb") as src:
        return await _ingest_audio(
            session, source.name, _read_chunks(src.read), title, artist, album
        )


async def _get_active(session: AsyncSession, song_id: uuid.UUID) -> Song:
    song = await repository.get_by_id(session, song_id)
    if song is None or not song.is_active:
        raise NotFound(_NOT_FOUND, code="song_not_found")
    return song


async def update_song(session: AsyncSession, song_id: uuid.UUID, data: SongUpdate) -> SongOut:
    song = await _get_active(session, song_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(song, field, value)
    await repository.save(session, song)
    return SongOut.model_validate(song)


async def deactivate_song(session: AsyncSession, song_id: uuid.UUID) -> None:
    song = await _get_active(session, song_id)
    song.is_active = False
    await repository.save(session, song)
