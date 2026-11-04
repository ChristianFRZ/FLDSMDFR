import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.catalog_schemas import SongOut
from app.modules.social.models import ArtistFollow, Favorite, NotificationRead


def _snapshot(song: SongOut) -> dict:
    return {
        "title_snapshot": song.title,
        "artist_snapshot": song.artist,
        "album_snapshot": song.album,
        "duration_snapshot": song.duration_seconds,
    }


async def add_favorite(session: AsyncSession, user_id: uuid.UUID, song: SongOut) -> None:
    stmt = insert(Favorite).values(user_id=user_id, song_id=song.id, **_snapshot(song))
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=[Favorite.user_id, Favorite.song_id], set_=_snapshot(song)
        )
    )
    await session.commit()


async def save_snapshots(session: AsyncSession, user_id: uuid.UUID, songs: list[SongOut]) -> None:
    """Actualiza la copia de las favoritas de `user_id` con los datos vivos del catálogo."""
    for song in songs:
        await session.execute(
            update(Favorite)
            .where(Favorite.user_id == user_id, Favorite.song_id == song.id)
            .values(**_snapshot(song))
        )
    await session.commit()


async def remove_favorite(session: AsyncSession, user_id: uuid.UUID, song_id: uuid.UUID) -> None:
    await session.execute(
        delete(Favorite).where(Favorite.user_id == user_id, Favorite.song_id == song_id)
    )
    await session.commit()


async def list_favorites(session: AsyncSession, user_id: uuid.UUID) -> list[Favorite]:
    stmt = (
        select(Favorite)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc(), Favorite.song_id)
    )
    return list((await session.scalars(stmt)).all())


async def add_follow(
    session: AsyncSession, user_id: uuid.UUID, artist_key: str, artist_name: str
) -> None:
    await session.execute(
        insert(ArtistFollow)
        .values(user_id=user_id, artist_key=artist_key, artist_name=artist_name)
        .on_conflict_do_nothing()
    )
    await session.commit()


async def remove_follow(session: AsyncSession, user_id: uuid.UUID, artist_key: str) -> None:
    await session.execute(
        delete(ArtistFollow).where(
            ArtistFollow.user_id == user_id, ArtistFollow.artist_key == artist_key
        )
    )
    await session.commit()


async def list_follows(session: AsyncSession, user_id: uuid.UUID) -> list[ArtistFollow]:
    stmt = (
        select(ArtistFollow)
        .where(ArtistFollow.user_id == user_id)
        .order_by(ArtistFollow.followed_at.desc(), ArtistFollow.artist_key)
    )
    return list((await session.scalars(stmt)).all())


async def read_ids(session: AsyncSession, user_id: uuid.UUID, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    stmt = select(NotificationRead.notification_id).where(
        NotificationRead.user_id == user_id, NotificationRead.notification_id.in_(ids)
    )
    return set((await session.scalars(stmt)).all())


async def mark_read(session: AsyncSession, user_id: uuid.UUID, ids: list[str]) -> None:
    if ids:
        await session.execute(
            insert(NotificationRead)
            .values([{"user_id": user_id, "notification_id": i} for i in set(ids)])
            .on_conflict_do_nothing()
        )
    await session.commit()
