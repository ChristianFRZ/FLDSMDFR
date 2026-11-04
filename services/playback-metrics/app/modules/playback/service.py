import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import catalog, users
from app.clients.catalog_schemas import SongOut
from app.clients.http import RemoteUnavailable
from app.modules.playback import repository
from app.modules.playback.schemas import (
    HistoryItemOut,
    HistoryPage,
    MetricsSummary,
    PlaybackIn,
    TopArtistOut,
    TopSongOut,
)

logger = logging.getLogger(__name__)

_UNAVAILABLE_TITLE = "Canción no disponible"
_BATCH_SIZE = 50
_TOP_ARTISTS_WINDOW = 500


async def record_playback(session: AsyncSession, user_id: uuid.UUID, data: PlaybackIn) -> bool:
    """True si el evento se conto; False si `playback_id` ya estaba registrado."""
    song = await catalog.get_song(data.song_id)  # 404 si no existe o esta inactiva
    return await repository.record_event(
        session,
        data.playback_id,
        song,  # guarda la copia para el historial degradado
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
            songs = await catalog.get_songs_by_ids([sid for sid, _ in batch])
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
                        song=song,
                    )
                )
    return result


async def total_playbacks(session: AsyncSession) -> int:
    return await repository.count_events(session)


async def summary(session: AsyncSession) -> MetricsSummary:
    """Si un servicio no responde, su total queda en None y el resumen se marca degradado."""
    total_songs = await _or_none(catalog.count_songs, "catalog-streaming")
    total_users = await _or_none(users.count_users, "users-playlists")
    return MetricsSummary(
        total_playbacks=await total_playbacks(session),
        total_songs=total_songs,
        total_users=total_users,
        top=await top_songs(session),
        degraded=total_songs is None or total_users is None,
    )


async def _or_none(fetch, service: str) -> int | None:
    try:
        return await fetch()
    except RemoteUnavailable:
        logger.warning("%s no disponible; el resumen se muestra degradado", service)
        return None


async def recent_for_user(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 20, offset: int = 0
) -> HistoryPage:
    rows, total = await repository.user_history(session, user_id, limit, offset)
    try:
        songs = await catalog.get_songs_by_ids([r.song_id for r in rows])
    except RemoteUnavailable:
        logger.warning("Catálogo no disponible; el historial se muestra con sus copias")
        return HistoryPage(items=[_degraded_item(r) for r in rows], total=total, degraded=True)
    items = [
        HistoryItemOut(
            song=songs[r.song_id],
            last_played_at=r.last_played_at,
            available=songs[r.song_id].is_active,
            status="ok" if songs[r.song_id].is_active else "unavailable",
        )
        for r in rows
        if r.song_id in songs
    ]
    await _refresh_snapshots(session, user_id, rows, songs)
    return HistoryPage(items=items, total=total)


def _degraded_item(row: repository.HistoryRow) -> HistoryItemOut:
    song = SongOut(
        id=row.song_id,
        title=row.title or _UNAVAILABLE_TITLE,
        artist=row.artist or "",
        album=row.album or "",
        duration_seconds=row.duration or 0,
        is_active=False,
        has_cover=False,
        created_at=row.last_played_at,
        size_bytes=0,
        mime_type="",
    )
    return HistoryItemOut(
        song=song, last_played_at=row.last_played_at, available=False, status="degraded"
    )


async def _refresh_snapshots(session, user_id, rows, songs) -> None:
    """Con el catálogo arriba, completa o corrige las copias que difieren de los datos vivos."""
    stale = [
        songs[r.song_id]
        for r in rows
        if r.song_id in songs
        and (r.title, r.artist, r.album, r.duration)
        != (
            songs[r.song_id].title,
            songs[r.song_id].artist,
            songs[r.song_id].album,
            songs[r.song_id].duration_seconds,
        )
    ]
    if not stale:
        return
    try:
        await repository.save_snapshots(session, user_id, stale)
    except Exception:
        logger.warning("No se pudieron guardar las copias del historial", exc_info=True)
        try:
            await session.rollback()
        except Exception:  # p. ej. la conexión se cayó: la lectura responde igual
            logger.warning("Tampoco se pudo deshacer la escritura de copias", exc_info=True)


async def top_artists(session: AsyncSession, limit: int = 5) -> list[TopArtistOut]:
    """Agrega las canciones más escuchadas por artista (clave normalizada)."""
    counts = await repository.top_counts(session, _TOP_ARTISTS_WINDOW)
    songs = await catalog.get_songs_by_ids([sid for sid, _ in counts])
    by_artist: dict[str, list[tuple[int, SongOut]]] = {}
    for sid, count in counts:
        song = songs.get(sid)
        if song is not None and song.is_active:
            key = catalog.normalize_artist(song.artist)
            by_artist.setdefault(key, []).append((count, song))
    ranked = sorted(by_artist.items(), key=lambda kv: -sum(c for c, _ in kv[1]))[:limit]
    song_counts = await catalog.count_active_by_artists([k for k, _ in ranked])
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
