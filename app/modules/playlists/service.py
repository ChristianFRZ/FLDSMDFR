import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import SongOut
from app.modules.playlists import repository
from app.modules.playlists.models import Playlist, PlaylistMember, PlaylistSong
from app.modules.playlists.schemas import (
    MemberOut,
    PlaylistDetail,
    PlaylistIn,
    PlaylistSongOut,
    PlaylistSummary,
    ReorderIn,
)
from app.modules.users import service as users_service
from app.shared.errors import Conflict, Forbidden, InvalidInput, NotFound
from app.shared.images import delete_image, save_image

logger = logging.getLogger(__name__)

_NOT_FOUND = "No encontramos ese casete."


def _role(playlist: Playlist, user_id: uuid.UUID) -> str:
    return "owner" if playlist.owner_id == user_id else "collaborator"


def _summary(
    playlist: Playlist, song_count: int, user_id: uuid.UUID | None = None
) -> PlaylistSummary:
    return PlaylistSummary(
        id=playlist.id,
        name=playlist.name,
        song_count=song_count,
        updated_at=playlist.updated_at,
        has_cover=playlist.cover_path is not None,
        role="owner" if user_id is None else _role(playlist, user_id),
    )


async def _get_readable(
    session: AsyncSession, user_id: uuid.UUID, playlist_id: uuid.UUID, for_update: bool = False
) -> Playlist:
    playlist = await repository.get_readable(session, user_id, playlist_id, for_update)
    if playlist is None:
        raise NotFound(_NOT_FOUND, code="playlist_not_found")
    return playlist


async def _members(session: AsyncSession, playlist_id: uuid.UUID) -> list[MemberOut]:
    members = []
    for m in await repository.list_members(session, playlist_id):
        try:
            name = (await users_service.get_user(session, m.user_id)).name
        except Exception:
            name = "Alguien"
        members.append(MemberOut(user_id=m.user_id, name=name))
    return members


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


async def _detail(session: AsyncSession, playlist: Playlist, user_id: uuid.UUID) -> PlaylistDetail:
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
        has_cover=playlist.cover_path is not None,
        role=_role(playlist, user_id),
        members=await _members(session, playlist.id),
    )


async def create_playlist(
    session: AsyncSession, owner_id: uuid.UUID, data: PlaylistIn
) -> PlaylistSummary:
    playlist = await repository.add(session, Playlist(owner_id=owner_id, name=data.name.strip()))
    await session.refresh(playlist)
    return _summary(playlist, 0)


async def list_playlists(session: AsyncSession, user_id: uuid.UUID) -> list[PlaylistSummary]:
    return [_summary(p, n, user_id) for p, n in await repository.list_with_counts(session, user_id)]


async def get_playlist(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID
) -> PlaylistDetail:
    return await _detail(session, await _get_readable(session, owner_id, playlist_id), owner_id)


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
    playlist = await _get_owned(session, owner_id, playlist_id, for_update=True)
    cover = playlist.cover_path
    await repository.delete_playlist(session, playlist)
    delete_image(_covers_dir(), cover)


async def add_song(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, song_id: uuid.UUID
) -> PlaylistDetail:
    playlist = await _get_readable(session, owner_id, playlist_id, for_update=True)
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
    return await _detail(session, playlist, owner_id)


def _duplicate() -> Conflict:
    return Conflict("Esa canción ya está en el casete.", code="song_already_in_playlist")


async def remove_song(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, song_id: uuid.UUID
) -> PlaylistDetail:
    playlist = await _get_readable(session, owner_id, playlist_id, for_update=True)
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
    return await _detail(session, playlist, owner_id)


async def reorder(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, data: ReorderIn
) -> PlaylistDetail:
    playlist = await _get_readable(session, owner_id, playlist_id, for_update=True)
    entries = {e.song_id: e for e in await repository.list_songs(session, playlist.id)}
    if len(data.song_ids) != len(entries) or set(data.song_ids) != set(entries):
        raise InvalidInput(
            "El orden debe incluir exactamente las canciones del casete.", code="invalid_order"
        )
    for position, song_id in enumerate(data.song_ids, start=1):
        entries[song_id].position = position
    repository.touch(playlist)
    await session.commit()
    return await _detail(session, playlist, owner_id)


def _covers_dir() -> Path:
    return get_settings().media_dir / "covers" / "playlists"


async def set_cover(
    session: AsyncSession, owner_id: uuid.UUID, playlist_id: uuid.UUID, upload: UploadFile
) -> PlaylistSummary:
    playlist = await _get_owned(session, owner_id, playlist_id, for_update=True)
    playlist.cover_path = await save_image(upload, _covers_dir(), str(playlist.id))
    repository.touch(playlist)
    await session.commit()
    return _summary(playlist, await repository.count_songs(session, playlist.id))


async def get_cover_file(session: AsyncSession, user_id: uuid.UUID, playlist_id: uuid.UUID) -> Path:
    playlist = await _get_readable(session, user_id, playlist_id)
    path = _covers_dir() / playlist.cover_path if playlist.cover_path else None
    if path is None or not path.is_file():
        raise NotFound("Este casete no tiene portada.", code="cover_not_found")
    return path


async def add_member(session: AsyncSession, playlist_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Uso interno (invitaciones): añade a la persona como colaboradora si aún no lo es."""
    if await repository.get_member(session, playlist_id, user_id) is None:
        session.add(PlaylistMember(playlist_id=playlist_id, user_id=user_id))
        await session.commit()


async def remove_member(
    session: AsyncSession, actor_id: uuid.UUID, playlist_id: uuid.UUID, member_id: uuid.UUID
) -> None:
    """El dueño quita a cualquiera; una colaboradora solo puede salir ella misma."""
    playlist = await _get_readable(session, actor_id, playlist_id, for_update=True)
    if playlist.owner_id != actor_id and actor_id != member_id:
        raise Forbidden("Solo quien creó el casete puede quitar colaboradores.")
    member = await repository.get_member(session, playlist.id, member_id)
    if member is None:
        raise NotFound("Esa persona no colabora en este casete.", code="member_not_found")
    await session.delete(member)
    await session.commit()
