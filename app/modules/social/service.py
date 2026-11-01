import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.social import repository
from app.modules.social.schemas import FavoriteSongOut, FavoritesOut

logger = logging.getLogger(__name__)


async def like(session: AsyncSession, user_id: uuid.UUID, song_id: uuid.UUID) -> None:
    await catalog_service.get_song(session, song_id)  # 404 si no existe o está inactiva
    await repository.add_favorite(session, user_id, song_id)


async def unlike(session: AsyncSession, user_id: uuid.UUID, song_id: uuid.UUID) -> None:
    await repository.remove_favorite(session, user_id, song_id)


async def favorite_ids(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    return [f.song_id for f in await repository.list_favorites(session, user_id)]


async def list_favorites(session: AsyncSession, user_id: uuid.UUID) -> FavoritesOut:
    favorites = await repository.list_favorites(session, user_id)
    songs = await catalog_service.get_songs_by_ids(session, [f.song_id for f in favorites])
    out = []
    for f in favorites:
        song = songs.get(f.song_id)
        if song is None:
            continue
        out.append(
            FavoriteSongOut(
                song_id=song.id,
                title=song.title,
                artist=song.artist,
                album=song.album,
                duration_seconds=song.duration_seconds,
                has_cover=song.has_cover,
                status="ok" if song.is_active else "unavailable",
                added_at=f.created_at,
            )
        )
    total = sum(s.duration_seconds for s in out if s.status == "ok")
    return FavoritesOut(songs=out, total_seconds=total)
