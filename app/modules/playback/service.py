import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import SongOut
from app.modules.playback import repository
from app.modules.playback.schemas import (
    HistoryItemOut,
    HistoryPage,
    MetricsSummary,
    PlaybackIn,
    TopArtistOut,
    TopSongOut,
)
from app.modules.users import service as users_service

logger = logging.getLogger(__name__)

_UNAVAILABLE_TITLE = "Canción no disponible"
_BATCH_SIZE = 50
_TOP_ARTISTS_WINDOW = 500


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


async def recent_for_user(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 20, offset: int = 0
) -> HistoryPage:
    rows, total = await repository.user_history(session, user_id, limit, offset)
    songs = await catalog_service.get_songs_by_ids(session, [sid for sid, _ in rows])
    items = [
        HistoryItemOut(song=songs[sid], last_played_at=at, available=songs[sid].is_active)
        for sid, at in rows
        if sid in songs
    ]
    return HistoryPage(items=items, total=total)


async def top_artists(session: AsyncSession, limit: int = 5) -> list[TopArtistOut]:
    """Agrega las canciones más escuchadas por artista (clave normalizada)."""
    counts = await repository.top_counts(session, _TOP_ARTISTS_WINDOW)
    songs = await catalog_service.get_songs_by_ids(session, [sid for sid, _ in counts])
    by_artist: dict[str, list[tuple[int, SongOut]]] = {}
    for sid, count in counts:
        song = songs.get(sid)
        if song is not None and song.is_active:
            key = catalog_service.normalize_artist(song.artist)
            by_artist.setdefault(key, []).append((count, song))
    ranked = sorted(by_artist.items(), key=lambda kv: -sum(c for c, _ in kv[1]))[:limit]
    song_counts = await catalog_service.count_active_by_artists(session, [k for k, _ in ranked])
    result = []
    for key, entries in ranked:
        with_cover = next((s for _, s in entries if s.has_cover), None)
        result.append(
            TopArtistOut(
                artist=entries[0][1].artist,
                play_count=sum(c for c, _ in entries),
                song_count=song_counts.get(key, 0),
                cover_song_id=(with_cover or entries[0][1]).id,
            )
        )
    return result
