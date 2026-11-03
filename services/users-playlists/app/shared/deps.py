from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import SessionLocal
from app.shared.errors import Forbidden, Unauthorized
from app.shared.security import TokenData, decode_access_token

CurrentUser = TokenData


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get(get_settings().cookie_name)
    if token:
        return token
    scheme, _, value = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return None


async def current_user(request: Request) -> TokenData:
    """Usuario autenticado a partir del JWT; no consulta la base de datos."""
    token = _extract_token(request)
    if token is None:
        raise Unauthorized("Necesitas iniciar sesión.")
    return decode_access_token(token)


async def require_admin(user: TokenData = Depends(current_user)) -> TokenData:
    if user.role != "admin":
        raise Forbidden("Solo las personas administradoras pueden hacer esto.")
    return user
