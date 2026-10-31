import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.catalog import repository
from app.modules.catalog.schemas import SongOut, SongPage
from app.shared.errors import NotFound

_NOT_FOUND = "No encontramos esa canción."


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
    path = get_settings().media_dir / song.file_path
    if not path.is_file():
        raise NotFound("El archivo de audio no está disponible.", code="audio_missing")
    return StreamFile(path=path, mime_type=song.mime_type, size=path.stat().st_size)


async def count_songs(session: AsyncSession) -> int:
    return await repository.count(session)
