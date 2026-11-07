import dataclasses
import logging
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.errors import AppError
from app.modules.catalog.public import get_songs
from app.modules.playlists.models import Playlist, PlaylistSong
from app.modules.playlists.schemas import PlaylistIn, PlaylistOut, PlaylistPatch

log = logging.getLogger(__name__)


async def create(session: AsyncSession, user: CurrentUser, data: PlaylistIn) -> Playlist:
    playlist = Playlist(owner_id=user.id, name=data.name, is_public=data.is_public)
    session.add(playlist)
    await session.commit()
    return playlist


async def list_mine(session: AsyncSession, user: CurrentUser) -> list[Playlist]:
    query = select(Playlist).where(Playlist.owner_id == user.id).order_by(Playlist.created_at.desc())
    return list((await session.execute(query)).scalars())


async def _load(session: AsyncSession, playlist_id: UUID) -> Playlist:
    playlist = await session.get(Playlist, playlist_id)
    if playlist is None:
        raise AppError(404, "playlist_not_found", "Playlist no encontrada")
    return playlist


async def _load_owned(session: AsyncSession, user: CurrentUser, playlist_id: UUID) -> Playlist:
    playlist = await _load(session, playlist_id)
    if playlist.owner_id != user.id:
        raise AppError(403, "forbidden", "Esta playlist no es tuya")
    return playlist


async def update(session: AsyncSession, user: CurrentUser, playlist_id: UUID, data: PlaylistPatch) -> Playlist:
    playlist = await _load_owned(session, user, playlist_id)
    for name, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(playlist, name, value)
    await session.commit()
    return playlist


async def delete(session: AsyncSession, user: CurrentUser, playlist_id: UUID) -> None:
    await session.delete(await _load_owned(session, user, playlist_id))
    await session.commit()


def _cache(summary) -> dict:
    return jsonable_encoder(dataclasses.asdict(summary))


async def add_song(session: AsyncSession, user: CurrentUser, playlist_id: UUID, song_id: UUID) -> bool:
    """Devuelve True si la agregó, False si ya estaba."""
    await _load_owned(session, user, playlist_id)
    try:
        songs = await get_songs([song_id])
    except Exception as exc:
        raise AppError(503, "catalog_unavailable", "El catálogo no responde. Intenta de nuevo.") from exc
    if song_id not in songs:
        raise AppError(404, "song_not_found", "Canción no encontrada")
    position = await session.scalar(
        select(func.coalesce(func.max(PlaylistSong.position), 0) + 1).where(PlaylistSong.playlist_id == playlist_id)
    )
    statement = (
        insert(PlaylistSong)
        .values(playlist_id=playlist_id, song_id=song_id, position=position, metadata_cache=_cache(songs[song_id]))
        .on_conflict_do_nothing()
        .returning(PlaylistSong.song_id)
    )
    added = (await session.execute(statement)).first() is not None
    await session.commit()
    return added


async def remove_song(session: AsyncSession, user: CurrentUser, playlist_id: UUID, song_id: UUID) -> None:
    await _load_owned(session, user, playlist_id)
    row = await session.get(PlaylistSong, (playlist_id, song_id))
    if row is not None:
        await session.delete(row)
        await session.commit()


async def detail(session: AsyncSession, user: CurrentUser, playlist_id: UUID) -> dict:
    playlist = await _load(session, playlist_id)
    if playlist.owner_id != user.id and not playlist.is_public:
        raise AppError(403, "forbidden", "Esta playlist es privada")
    query = select(PlaylistSong).where(PlaylistSong.playlist_id == playlist_id).order_by(PlaylistSong.position)
    rows = list((await session.execute(query)).scalars())
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    degraded = False
    songs = {}
    try:
        songs = await get_songs([r.song_id for r in rows])
    except Exception:
        log.warning("Catálogo no disponible: playlist %s con metadatos en caché", playlist_id)
        degraded = True
    items = []
    for row in rows:
        summary = songs.get(row.song_id)
        if summary is not None:
            fresh = _cache(summary)
            if fresh != row.metadata_cache:
                row.metadata_cache = fresh
            items.append(fresh)
        else:
            # Sin catálogo se confía en la caché; si el catálogo responde y no la tiene, la pista ya no existe.
            items.append({**row.metadata_cache, "available": degraded and row.metadata_cache.get("available", False)})
    await session.commit()
    return {**PlaylistOut.model_validate(playlist).model_dump(), "degraded": degraded, "songs": items}
