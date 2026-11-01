import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.social.models import Favorite


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
