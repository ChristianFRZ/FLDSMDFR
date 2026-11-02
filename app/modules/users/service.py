import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users import repository
from app.modules.users.models import User
from app.modules.users.schemas import RegisterIn, Role, UserOut
from app.shared.errors import Conflict, Forbidden, NotFound, Unauthorized
from app.shared.security import hash_password, verify_password

_EMAIL_TAKEN = "Ese correo ya está registrado."


def _normalize(email: str) -> str:
    return email.strip().lower()


async def _create(
    session: AsyncSession, name: str, email: str, password: str, role: Role
) -> UserOut:
    user = User(
        name=name,
        email=_normalize(email),
        password_hash=hash_password(password),
        role=role,
    )
    try:
        await repository.add(session, user)
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict(_EMAIL_TAKEN, code="email_taken") from exc
    return UserOut.model_validate(user)


async def register(session: AsyncSession, data: RegisterIn) -> UserOut:
    if await repository.get_by_email(session, _normalize(data.email)):
        raise Conflict(_EMAIL_TAKEN, code="email_taken")
    return await _create(session, data.name, data.email, data.password, "listener")


async def authenticate(session: AsyncSession, email: str, password: str) -> UserOut:
    user = await repository.get_by_email(session, _normalize(email))
    if user is None or not verify_password(password, user.password_hash):
        raise Unauthorized("Correo o contraseña incorrectos.")
    return UserOut.model_validate(user)


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> UserOut:
    user = await repository.get_by_id(session, user_id)
    if user is None:
        raise NotFound("No encontramos a esa persona.")
    return UserOut.model_validate(user)


async def list_users(session: AsyncSession, q: str | None) -> list[UserOut]:
    users = await repository.search(session, q.strip() if q else None)
    return [UserOut.model_validate(u) for u in users]


async def set_role(
    session: AsyncSession, actor_id: uuid.UUID, user_id: uuid.UUID, role: Role
) -> UserOut:
    if actor_id == user_id and role == "listener":
        raise Forbidden("No puedes quitarte el rol de administrador.")
    user = await repository.get_by_id(session, user_id)
    if user is None:
        raise NotFound("No encontramos a esa persona.")
    user.role = role
    await repository.save(session, user)
    return UserOut.model_validate(user)


async def count_users(session: AsyncSession) -> int:
    return await repository.count(session)


async def ensure_user(
    session: AsyncSession, name: str, email: str, password: str, role: Role
) -> UserOut:
    existing = await repository.get_by_email(session, _normalize(email))
    if existing is not None:
        return UserOut.model_validate(existing)
    return await _create(session, name, email, password, role)
