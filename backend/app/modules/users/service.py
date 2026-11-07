import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from uuid import UUID

import anyio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    hash_opaque_token,
    hash_password,
    new_opaque_token,
    verify_password,
)
from app.modules.users.models import RefreshToken, User
from app.modules.users.schemas import RegisterIn, TokenOut

REFRESH_DAYS = 30
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 60
# Hash fijo para gastar el mismo tiempo cuando el correo no existe.
_DUMMY_HASH = hash_password("cuenta-inexistente")


class LoginLimiter:
    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str) -> deque[float]:
        attempts = self._failures[key]
        limit = time.monotonic() - LOGIN_WINDOW_SECONDS
        while attempts and attempts[0] < limit:
            attempts.popleft()
        return attempts

    def check(self, key: str) -> None:
        if len(self._recent(key)) >= LOGIN_MAX_FAILURES:
            raise AppError(429, "too_many_attempts", "Demasiados intentos. Espera un minuto.")

    def fail(self, key: str) -> None:
        self._failures[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        self._failures.pop(key, None)


login_limiter = LoginLimiter()


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def _issue_tokens(session: AsyncSession, user: User) -> TokenOut:
    refresh = new_opaque_token()
    session.add(
        RefreshToken(
            token_hash=hash_opaque_token(refresh),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_DAYS),
        )
    )
    await session.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role), refresh_token=refresh)


async def create_user(
    session: AsyncSession, email: str, password: str, display_name: str, role: str = "listener"
) -> User:
    password_hash = await anyio.to_thread.run_sync(hash_password, password)
    user = User(email=normalize_email(email), password_hash=password_hash, display_name=display_name, role=role)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(409, "email_taken", "Ese correo ya tiene cuenta") from exc
    return user


async def register(session: AsyncSession, data: RegisterIn) -> TokenOut:
    user = await create_user(session, data.email, data.password, data.display_name)
    return await _issue_tokens(session, user)


async def login(session: AsyncSession, email: str, password: str, client_ip: str) -> TokenOut:
    email = normalize_email(email)
    key = f"{email}|{client_ip}"
    login_limiter.check(key)
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    stored_hash = user.password_hash if user else _DUMMY_HASH
    valid = await anyio.to_thread.run_sync(verify_password, password, stored_hash)
    if user is None or not valid:
        login_limiter.fail(key)
        raise AppError(401, "invalid_credentials", "Correo o contraseña incorrectos")
    if user.status != "active":
        raise AppError(403, "account_suspended", "Esta cuenta está suspendida")
    login_limiter.clear(key)
    return await _issue_tokens(session, user)


async def refresh(session: AsyncSession, token: str) -> TokenOut:
    invalid = AppError(401, "invalid_refresh", "La sesión venció. Entra de nuevo.")
    stored = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(token)).with_for_update()
        )
    ).scalar_one_or_none()
    if stored is None or stored.revoked_at is not None or stored.expires_at < datetime.now(UTC):
        raise invalid
    stored.revoked_at = datetime.now(UTC)
    user = await session.get(User, stored.user_id)
    if user is None or user.status != "active":
        await session.commit()
        raise invalid
    return await _issue_tokens(session, user)


async def logout(session: AsyncSession, token: str) -> None:
    stored = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(token)))
    ).scalar_one_or_none()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await session.commit()


async def get_user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "Usuario no encontrado")
    return user


async def update_profile(session: AsyncSession, user_id: UUID, display_name: str) -> User:
    user = await get_user(session, user_id)
    user.display_name = display_name
    await session.commit()
    return user
