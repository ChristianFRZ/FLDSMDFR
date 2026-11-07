"""Interfaz pública de modules.users. Solo tipos simples; cada función abre su sesión."""
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.core.db import session_scope
from app.core.errors import AppError
from app.modules.users import admin, service
from app.modules.users.models import User
from app.modules.users.demo import DemoUser, clear_demo_users, demo_user_ids, insert_demo_users  # noqa: F401


@dataclass(frozen=True)
class AuthState:
    id: UUID
    role: str
    status: str


@dataclass(frozen=True)
class UserGrowthPoint:
    day: date
    listener: int
    composer: int
    admin: int


async def get_auth_state(user_id: UUID) -> AuthState | None:
    async with session_scope() as session:
        row = (await session.execute(select(User.id, User.role, User.status).where(User.id == user_id))).first()
    return AuthState(*row) if row else None


async def get_display_names(ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    async with session_scope() as session:
        rows = (await session.execute(select(User.id, User.display_name).where(User.id.in_(ids)))).all()
    return {row.id: row.display_name for row in rows}


async def ensure_first_admin(email: str, password: str) -> None:
    """Crea el primer administrador si no hay ninguno. Seguro con dos procesos arrancando a la vez."""
    async with session_scope() as session:
        existing = await session.scalar(select(func.count()).select_from(User).where(User.role == "admin"))
        if existing:
            return
        try:
            await service.create_user(session, email, password, "Administrador", role="admin")
        except AppError:
            return


async def record_audit(
    actor_id: UUID | str | None,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict | None = None,
    outcome: str = "ok",
) -> None:
    actor = UUID(str(actor_id)) if actor_id else None
    await admin.write_audit(actor, action, target_type, str(target_id), detail, outcome)


async def user_growth(days: int) -> list[UserGrowthPoint]:
    """Usuarios acumulados por rol actual al final de cada día. Sin historial de cambios de rol."""
    today = datetime.now(UTC).date()
    first = today - timedelta(days=days - 1)
    async with session_scope() as session:
        created_on = func.date(User.created_at)
        query = select(User.role, created_on, func.count()).group_by(User.role, created_on)
        rows = (await session.execute(query)).all()
    points = []
    for offset in range(days):
        day = first + timedelta(days=offset)
        totals = {"listener": 0, "composer": 0, "admin": 0}
        for role, created, count in rows:
            if created <= day and role in totals:
                totals[role] += count
        points.append(UserGrowthPoint(day=day, **totals))
    return points
