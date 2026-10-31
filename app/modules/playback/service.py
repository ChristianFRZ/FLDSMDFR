import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.playback import repository
from app.modules.playback.schemas import MetricsSummary, PlaybackIn, TopSongOut
from app.modules.users import service as users_service

logger = logging.getLogger(__name__)

_UNAVAILABLE_TITLE = "Canción no disponible"
_BATCH_SIZE = 50


async def record_playback(session: AsyncSession, user_id: uuid.UUID, data: PlaybackIn) -> bool:
    """True si el evento se conto; False si `playback_id` ya estaba registrado."""
    await catalog_service.get_song(session, data.song_id)  # 404 si no existe o esta inactiva
    return await repository.record_event(
        session,
        data.playback_id,
        data.song_id,
        user_id,
        data.listened_seconds,
        data.occurred_at or datetime.now(UTC),
    )


async def top_songs(session: AsyncSession, limit: int = 10) -> list[TopSongOut]:
    result: list[TopSongOut] = []
    offset = 0
    # Las canciones inactivas se omiten, asi que se leen lotes hasta completar `limit`.
    while len(result) < limit:
        batch = await repository.top_counts(session, max(limit, _BATCH_SIZE), offset)
        if not batch:
            break
        offset += len(batch)
        try:
            songs = await catalog_service.get_songs_by_ids(session, [sid for sid, _ in batch])
        except Exception:
            logger.warning("Catálogo no disponible; el top se muestra degradado", exc_info=True)
            return [
                TopSongOut(
                    song_id=sid, title=_UNAVAILABLE_TITLE, artist="", album="", play_count=count
                )
                for sid, count in batch
            ][:limit]
        for sid, count in batch:
            song = songs.get(sid)
            if song is not None and song.is_active and len(result) < limit:
                result.append(
                    TopSongOut(
                        song_id=sid,
                        title=song.title,
                        artist=song.artist,
                        album=song.album,
                        play_count=count,
                    )
                )
    return result


async def total_playbacks(session: AsyncSession) -> int:
    return await repository.count_events(session)


async def summary(session: AsyncSession) -> MetricsSummary:
    return MetricsSummary(
        total_playbacks=await total_playbacks(session),
        total_songs=await catalog_service.count_songs(session),
        total_users=await users_service.count_users(session),
        top=await top_songs(session),
    )
