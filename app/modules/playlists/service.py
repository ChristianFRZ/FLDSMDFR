import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import SongOut
from app.modules.playlists import repository
from app.modules.playlists.models import Playlist, PlaylistSong
from app.modules.playlists.schemas import (
    PlaylistDetail,
    PlaylistIn,
    PlaylistSongOut,
    PlaylistSummary,
    ReorderIn,
)
from app.shared.errors import Conflict, InvalidInput, NotFound

logger = logging.getLogger(__name__)

_NOT_FOUND = "No encontramos ese casete."


def _summary(playlist: Playlist, song_count: int) -> PlaylistSummary:
    return PlaylistSummary(
        id=playlist.id, name=playlist.name, song_count=song_count, updated_at=playlist.updated_at
    )


async def _get_owned(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, for_update: bool = False
) -> Playlist:
    playlist = await repository.get_owned(session, owner_id, playlist_id, for_update)
    if playlist is None:
        raise NotFound(_NOT_FOUND, code="playlist_not_found")
    return playlist


def _song_out(entry: PlaylistSong, status: str, fresh: SongOut | None = None) -> PlaylistSongOut:
    return PlaylistSongOut(
        song_id=entry.song_id,
        title=fresh.title if fresh else entry.title_snapshot,
        artist=fresh.artist if fresh else entry.artist_snapshot,
        album=fresh.album if fresh else entry.album_snapshot,
        duration_seconds=fresh.duration_seconds if fresh else entry.duration_snapshot,
        position=entry.position,
        status=status,
    )


async def _detail(session: AsyncSession, playlist: Playlist) -> PlaylistDetail:
    entries = await repository.list_songs(session, playlist.id)
    songs: list[PlaylistSongOut]
    try:
        fresh = await catalog_service.get_songs_by_ids(session, [e.song_id for e in entries])
    except Exception:
        logger.warning(
            "Catálogo no disponible; el casete %s se muestra en modo degradado",
            playlist.id,
            exc_info=True,
        )
        songs = [_song_out(e, "degraded") for e in entries]
    else:
        songs = []
        for e in entries:
            song = fresh.get(e.song_id)
            if song is None or not song.is_active:
                songs.append(_song_out(e, "unavailable"))
            else:
                songs.append(_song_out(e, "ok", song))
    return PlaylistDetail(
        id=playlist.id,
        name=playlist.name,
        songs=songs,
        total_seconds=sum(s.duration_seconds for s in songs),
    )


async def create_playlist(
    session: AsyncSession, owner_id: uuid.UUID, data: PlaylistIn
) -> PlaylistSummary:
    playlist = await repository.add(session, Playlist(owner_id=owner_id, name=data.name.strip()))
    await session.refresh(playlist)
    return _summary(playlist, 0)


async def list_playlists(session: AsyncSession, owner_id: uuid.UUID) -> list[PlaylistSummary]:
    return [_summary(p, n) for p, n in await repository.list_with_counts(session, owner_id)]


async def get_playlist(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID
) -> PlaylistDetail:
    return await _detail(session, await _get_owned(session, owner_id, playlist_id))


async def rename_playlist(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, data: PlaylistIn
) -> PlaylistSummary:
    playlist = await _get_owned(session, owner_id, playlist_id, for_update=True)
    playlist.name = data.name.strip()
    repository.touch(playlist)
    await session.commit()
    return _summary(playlist, await repository.count_songs(session, playlist.id))


async def delete_playlist(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID
) -> None:
    await repository.delete_playlist(
        session, await _get_owned(session, owner_id, playlist_id, for_update=True)
    )


async def add_song(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, song_id: uuid.UUID
) -> PlaylistDetail:
    playlist = await _get_owned(session, owner_id, playlist_id, for_update=True)
    song = await catalog_service.get_song(session, song_id)
    if await repository.get_entry(session, playlist.id, song_id) is not None:
        raise _duplicate()
    session.add(
        PlaylistSong(
            playlist_id=playlist.id,
            song_id=song.id,
            position=await repository.max_position(session, playlist.id) + 1,
            title_snapshot=song.title,
            artist_snapshot=song.artist,
            album_snapshot=song.album,
            duration_snapshot=song.duration_seconds,
        )
    )
    repository.touch(playlist)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise _duplicate() from None
    return await _detail(session, playlist)


def _duplicate() -> Conflict:
    return Conflict("Esa canción ya está en el casete.", code="song_already_in_playlist")


async def remove_song(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, song_id: uuid.UUID
) -> PlaylistDetail:
    playlist = await _get_owned(session, owner_id, playlist_id, for_update=True)
    entry = await repository.get_entry(session, playlist.id, song_id)
    if entry is None:
        raise NotFound("Esa canción no está en el casete.", code="song_not_in_playlist")
    await repository.delete_entry(session, entry)
    remaining = [
        e for e in await repository.list_songs(session, playlist.id) if e.song_id != song_id
    ]
    for position, e in enumerate(remaining, start=1):
        e.position = position
    repository.touch(playlist)
    await session.commit()
    return await _detail(session, playlist)


async def reorder(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, data: ReorderIn
) -> PlaylistDetail:
    playlist = await _get_owned(session, owner_id, playlist_id, for_update=True)
    entries = {e.song_id: e for e in await repository.list_songs(session, playlist.id)}
    if len(data.song_ids) != len(entries) or set(data.song_ids) != set(entries):
        raise InvalidInput(
            "El orden debe incluir exactamente las canciones del casete.", code="invalid_order"
        )
    for position, song_id in enumerate(data.song_ids, start=1):
        entries[song_id].position = position
    repository.touch(playlist)
    await session.commit()
    return await _detail(session, playlist)
