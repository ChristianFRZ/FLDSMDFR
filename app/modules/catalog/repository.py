import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Song


def _like_pattern(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _active_filter(q: str | None):
    conditions = [Song.is_active.is_(True)]
    if q:
        pattern = _like_pattern(q)
        conditions.append(
            or_(
                Song.title.ilike(pattern, escape="\\"),
                Song.artist.ilike(pattern, escape="\\"),
                Song.album.ilike(pattern, escape="\\"),
            )
        )
    return conditions


async def search_active(
    session: AsyncSession, q: str | None, limit: int, offset: int
) -> tuple[list[Song], int]:
    conditions = _active_filter(q)
    total = await session.scalar(select(func.count()).select_from(Song).where(*conditions))
    stmt = select(Song).where(*conditions).order_by(Song.title, Song.id).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all()), total or 0


async def get_by_id(session: AsyncSession, song_id: uuid.UUID) -> Song | None:
    return await session.get(Song, song_id)


async def get_by_ids(session: AsyncSession, ids: Sequence[uuid.UUID]) -> list[Song]:
    if not ids:
        return []
    return list((await session.scalars(select(Song).where(Song.id.in_(ids)))).all())


async def add(session: AsyncSession, song: Song) -> Song:
    session.add(song)
    await session.commit()
    return song


async def count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Song)) or 0


async def save(session: AsyncSession, song: Song) -> Song:
    await session.commit()
    return song


async def find_by_title_artist(session: AsyncSession, title: str, artist: str) -> Song | None:
    stmt = (
        select(Song)
        .where(func.lower(Song.title) == title.lower(), func.lower(Song.artist) == artist.lower())
        .order_by(Song.created_at, Song.id)
        .limit(1)
    )
    return await session.scalar(stmt)
