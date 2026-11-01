import logging
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.social import repository
from app.modules.social.schemas import FavoriteSongOut, FavoritesOut, FollowOut
from app.shared.errors import NotFound

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


async def follow(session: AsyncSession, user_id: uuid.UUID, artist: str) -> None:
    key = catalog_service.normalize_artist(artist)
    latest = (await catalog_service.latest_song_by_artists(session, [key])).get(key)
    if latest is None:
        raise NotFound("No encontramos a ese artista en el catálogo.", code="artist_not_found")
    await repository.add_follow(session, user_id, key, latest.artist)


async def unfollow(session: AsyncSession, user_id: uuid.UUID, artist: str) -> None:
    await repository.remove_follow(session, user_id, catalog_service.normalize_artist(artist))


async def followed_artists(session: AsyncSession, user_id: uuid.UUID) -> list[FollowOut]:
    follows = await repository.list_follows(session, user_id)
    keys = [f.artist_key for f in follows]
    counts = await catalog_service.count_active_by_artists(session, keys)
    latest = await catalog_service.latest_song_by_artists(session, keys)
    out = []
    for f in follows:
        song = latest.get(f.artist_key)
        out.append(
            FollowOut(
                artist=f.artist_name,
                followed_at=f.followed_at,
                song_count=counts.get(f.artist_key, 0),
                cover_song_id=song.id if song is not None and song.has_cover else None,
            )
        )
    return out


async def follows_for_releases(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[str, datetime]]:
    return [(f.artist_key, f.followed_at) for f in await repository.list_follows(session, user_id)]
