import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email))


async def add(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.commit()
    return user


async def search(session: AsyncSession, q: str | None, limit: int = 50) -> list[User]:
    stmt = select(User).order_by(User.created_at, User.email).limit(limit)
    if q:
        pattern = f"%{q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')}%"
        stmt = stmt.where(
            or_(User.name.ilike(pattern, escape="\\"), User.email.ilike(pattern, escape="\\"))
        )
    return list((await session.scalars(stmt)).all())


async def count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(User)) or 0


async def save(session: AsyncSession, user: User) -> User:
    await session.commit()
    return user
