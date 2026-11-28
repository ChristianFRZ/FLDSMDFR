import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from meloxo_common.auth import CurrentUser
from meloxo_common.errors import AppError
from meloxo_common.pagination import PageParams, page_body
from meloxo_common.contracts import ArtistSummary, PublishedRelease, SongSummary
from users_playlists.clients.catalog import (
    RECENT_LIMIT,
    get_artists,
    get_songs,
    missing_song,
    published_since,
    upcoming_for_artists,
)
from users_playlists.modules.social.models import Favorite, Follow, NoticeSeen, ReleaseEvent
from users_playlists.modules.social.tapes import pending_invites

log = logging.getLogger(__name__)

RECENT_RELEASES = 12


async def add_favorite(session: AsyncSession, user: CurrentUser, song_id: UUID) -> None:
    if song_id not in await get_songs([song_id]):
        raise AppError(404, "song_not_found", "Canción no encontrada")
    await session.execute(insert(Favorite).values(user_id=user.id, song_id=song_id).on_conflict_do_nothing())
    await session.commit()


async def remove_favorite(session: AsyncSession, user: CurrentUser, song_id: UUID) -> None:
    await session.execute(delete(Favorite).where(Favorite.user_id == user.id, Favorite.song_id == song_id))
    await session.commit()


async def list_favorites(session: AsyncSession, user: CurrentUser, params: PageParams) -> dict:
    mine = Favorite.user_id == user.id
    total = await session.scalar(select(func.count()).select_from(Favorite).where(mine))
    query = (
        select(Favorite.song_id)
        .where(mine)
        .order_by(Favorite.created_at.desc())
        .limit(params.size)
        .offset((params.page - 1) * params.size)
    )
    ids = list((await session.execute(query)).scalars())
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    songs = await get_songs(ids)
    return page_body([songs.get(i) or missing_song(i) for i in ids], total, params)


async def favorite_ids(session: AsyncSession, user: CurrentUser) -> list[UUID]:
    return list((await session.execute(select(Favorite.song_id).where(Favorite.user_id == user.id))).scalars())


async def follow(session: AsyncSession, user: CurrentUser, artist_id: UUID) -> None:
    if artist_id not in await get_artists([artist_id]):
        raise AppError(404, "artist_not_found", "Artista no encontrado")
    await session.execute(insert(Follow).values(user_id=user.id, artist_id=artist_id).on_conflict_do_nothing())
    await session.commit()


async def unfollow(session: AsyncSession, user: CurrentUser, artist_id: UUID) -> None:
    await session.execute(delete(Follow).where(Follow.user_id == user.id, Follow.artist_id == artist_id))
    await session.commit()


async def followed_artists(session: AsyncSession, user: CurrentUser) -> dict:
    """Artistas seguidos y desde cuándo."""
    query = select(Follow.artist_id, Follow.created_at).where(Follow.user_id == user.id)
    followed = dict((await session.execute(query)).all())
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    return followed


async def list_follows(session: AsyncSession, user: CurrentUser) -> list[ArtistSummary]:
    return list((await get_artists(list(await followed_artists(session, user)))).values())


async def local_releases(session: AsyncSession, artist_ids: list[UUID], since: datetime | None) -> list[PublishedRelease]:
    """Lanzamientos guardados por el consumidor de `track_published`: no llama a catálogo.

    Un `song` guardado que ya no valide como `SongSummary` se omite con un aviso en el log.
    """
    if not artist_ids:
        return []
    query = select(ReleaseEvent).where(ReleaseEvent.artist_id.in_(artist_ids))
    if since is not None:
        query = query.where(ReleaseEvent.published_at > since)
    rows = (await session.execute(query.order_by(ReleaseEvent.published_at.desc()).limit(RECENT_LIMIT))).scalars()
    found = []
    for row in rows:
        try:
            found.append(PublishedRelease(song=SongSummary.model_validate(row.song), published_at=row.published_at))
        except ValueError:
            log.warning("El lanzamiento %s guardado no es válido; se omite", row.song_id)
    return found


async def notices(session: AsyncSession, user: CurrentUser) -> dict:
    seen = await session.scalar(select(NoticeSeen.seen_at).where(NoticeSeen.user_id == user.id))
    followed = await followed_artists(session, user)
    items = []
    if followed:
        earliest = min(followed.values())
        releases = await local_releases(session, list(followed), max(earliest, seen) if seen else earliest)
        # Seguir a un artista no avisa de lo que ya había publicado.
        items = [
            {"type": "release", "song": r.song, "published_at": r.published_at}
            for r in releases
            if r.published_at > followed[r.song.artist_id]
        ]
    invites = [{"type": "invite", **i} for i in await pending_invites(session, user)]
    items = invites + items
    return {"unread": len(items), "items": items, "degraded": False}  # ya no depende de catálogo


async def mark_seen(session: AsyncSession, user: CurrentUser) -> None:
    statement = insert(NoticeSeen).values(user_id=user.id)
    await session.execute(
        statement.on_conflict_do_update(index_elements=[NoticeSeen.user_id], set_={"seen_at": func.now()})
    )
    await session.commit()


async def releases(session: AsyncSession, user: CurrentUser) -> dict:
    followed = list(await followed_artists(session, user))
    try:
        scheduled = await upcoming_for_artists(followed)
        published = (await published_since(followed, None))[:RECENT_RELEASES]
    except Exception:
        log.warning("Catálogo no disponible: lanzamientos vacíos")
        return {"scheduled": [], "published": [], "degraded": True}
    return {"scheduled": scheduled, "published": published, "degraded": False}
