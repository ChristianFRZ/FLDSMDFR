import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.social.models import ArtistFollow, Favorite, NotificationRead


async def add_favorite(session: AsyncSession, user_id: uuid.UUID, song_id: uuid.UUID) -> None:
    await session.execute(
        insert(Favorite).values(user_id=user_id, song_id=song_id).on_conflict_do_nothing()
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
