import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import catalog
from app.clients.http import RemoteUnavailable
from app.modules.playlists import service as playlists_service
from app.modules.social import repository
from app.modules.social.schemas import (
    FavoriteSongOut,
    FavoritesOut,
    FollowOut,
    InviteNotice,
    NotificationOut,
    NotificationsOut,
)
from app.modules.users import service as users_service
from app.shared.errors import NotFound

logger = logging.getLogger(__name__)


UNAVAILABLE_TITLE = "Canción no disponible"


async def like(session: AsyncSession, user_id: uuid.UUID, song_id: uuid.UUID) -> None:
    song = await catalog.get_song(song_id)  # 404 si no existe o está inactiva
    await repository.add_favorite(session, user_id, song)  # guarda la copia para el modo degradado


async def unlike(session: AsyncSession, user_id: uuid.UUID, song_id: uuid.UUID) -> None:
    await repository.remove_favorite(session, user_id, song_id)


async def favorite_ids(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    return [f.song_id for f in await repository.list_favorites(session, user_id)]


async def list_favorites(session: AsyncSession, user_id: uuid.UUID) -> FavoritesOut:
    favorites = await repository.list_favorites(session, user_id)
    try:
        songs = await catalog.get_songs_by_ids([f.song_id for f in favorites])
    except RemoteUnavailable:
        logger.warning("Catálogo no disponible; las favoritas se muestran con sus copias")
        return _degraded_favorites(favorites)
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
    # Al final: si el commit falla, el rollback expira los objetos y ya no se leen.
    await _refresh_snapshots(session, user_id, favorites, songs)
    return FavoritesOut(songs=out, total_seconds=total)


def _degraded_favorites(favorites) -> FavoritesOut:
    out = [
        FavoriteSongOut(
            song_id=f.song_id,
            title=f.title_snapshot or UNAVAILABLE_TITLE,
            artist=f.artist_snapshot or "",
            album=f.album_snapshot or "",
            duration_seconds=f.duration_snapshot or 0,
            has_cover=False,
            status="degraded",
            added_at=f.created_at,
        )
        for f in favorites
    ]
    return FavoritesOut(
        songs=out, total_seconds=sum(s.duration_seconds for s in out), degraded=True
    )


async def _refresh_snapshots(session, user_id, favorites, songs) -> None:
    """Con el catálogo arriba, completa o corrige las copias que difieren de los datos vivos."""
    stale = [
        songs[f.song_id]
        for f in favorites
        if f.song_id in songs
        and (f.title_snapshot, f.artist_snapshot, f.album_snapshot, f.duration_snapshot)
        != (
            songs[f.song_id].title,
            songs[f.song_id].artist,
            songs[f.song_id].album,
            songs[f.song_id].duration_seconds,
        )
    ]
    if not stale:
        return
    try:
        await repository.save_snapshots(session, user_id, stale)
    except Exception:
        logger.warning("No se pudieron guardar las copias de favoritas", exc_info=True)
        try:
            await session.rollback()
        except Exception:  # p. ej. la conexión se cayó: la lectura responde igual
            logger.warning("Tampoco se pudo deshacer la escritura de copias", exc_info=True)


async def follow(session: AsyncSession, user_id: uuid.UUID, artist: str) -> None:
    key = catalog.normalize_artist(artist)
    latest = (await catalog.latest_song_by_artists([key])).get(key)
    if latest is None:
        raise NotFound("No encontramos a ese artista en el catálogo.", code="artist_not_found")
    await repository.add_follow(session, user_id, key, latest.artist)


async def unfollow(session: AsyncSession, user_id: uuid.UUID, artist: str) -> None:
    await repository.remove_follow(session, user_id, catalog.normalize_artist(artist))


async def followed_artists(session: AsyncSession, user_id: uuid.UUID) -> list[FollowOut]:
    follows = await repository.list_follows(session, user_id)
    keys = [f.artist_key for f in follows]
    counts = await catalog.count_active_by_artists(keys)
    latest = await catalog.latest_song_by_artists(keys)
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


_RELEASE_WINDOW = timedelta(days=30)


async def _release_notices(session: AsyncSession, user_id: uuid.UUID) -> list[NotificationOut]:
    follows = await follows_for_releases(session, user_id)
    if not follows:
        return []
    not_before = datetime.now(UTC) - _RELEASE_WINDOW
    songs = await catalog.songs_by_artists_since(follows, not_before)
    return [
        NotificationOut(
            id=f"release:{s.id}", type="release", created_at=s.created_at, read=False, song=s
        )
        for s in songs
    ]


async def _inviter_name(session: AsyncSession, user_id: uuid.UUID) -> str:
    try:
        return (await users_service.get_user(session, user_id)).name
    except Exception:
        return "Alguien"


async def _invite_notices(session: AsyncSession, user_id: uuid.UUID) -> list[NotificationOut]:
    notices = []
    for p in await playlists_service.pending_invites_for(session, user_id):
        notices.append(
            NotificationOut(
                id=f"invite:{p.token}",
                type="invite",
                created_at=p.claimed_at,
                read=False,
                invite=InviteNotice(
                    token=p.token,
                    playlist_id=p.playlist_id,
                    playlist_name=p.playlist_name,
                    inviter_name=await _inviter_name(session, p.invited_by),
                ),
            )
        )
    return notices


async def notifications_for(session: AsyncSession, user_id: uuid.UUID) -> NotificationsOut:
    """Avisos calculados al leerlos; si una fuente falla se omite (modo degradado)."""
    items: list[NotificationOut] = []
    for source in (_release_notices, _invite_notices):
        try:
            items.extend(await source(session, user_id))
        except Exception:
            await session.rollback()
            logger.warning("Fuente de avisos no disponible: %s", source.__name__, exc_info=True)
    read = await repository.read_ids(session, user_id, [n.id for n in items])
    for n in items:
        n.read = n.id in read
    items.sort(key=lambda n: n.created_at, reverse=True)
    return NotificationsOut(items=items, unread_count=sum(not n.read for n in items))


async def mark_read(session: AsyncSession, user_id: uuid.UUID, ids: list[str]) -> None:
    await repository.mark_read(session, user_id, ids)
