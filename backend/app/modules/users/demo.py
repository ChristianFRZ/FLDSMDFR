"""Usuarios ficticios de la semilla de demo. Nada de esto corre en el arranque normal."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select

from app.core.db import session_scope
from app.core.security import hash_password
from app.modules.users.models import ComposerRequest, User


@dataclass(frozen=True)
class DemoUser:
    email: str
    display_name: str
    role: str
    created_at: datetime
    request_message: str | None = None


async def insert_demo_users(users: list[DemoUser], password: str) -> dict[str, UUID]:
    """Devuelve el id de cada correo. Comparten contraseña: argon2 es lento a propósito."""
    password_hash = hash_password(password)
    async with session_scope() as session:
        rows = {
            user.email: User(
                email=user.email,
                password_hash=password_hash,
                display_name=user.display_name,
                role=user.role,
                created_at=user.created_at,
                is_demo=True,
            )
            for user in users
        }
        session.add_all(rows.values())
        await session.flush()
        session.add_all(
            ComposerRequest(user_id=rows[user.email].id, message=user.request_message)
            for user in users
            if user.request_message
        )
        return {email: row.id for email, row in rows.items()}


async def demo_user_ids() -> list[UUID]:
    async with session_scope() as session:
        return list(await session.scalars(select(User.id).where(User.is_demo.is_(True))))


async def clear_demo_users() -> None:
    async with session_scope() as session:
        await session.execute(delete(User).where(User.is_demo.is_(True)))
