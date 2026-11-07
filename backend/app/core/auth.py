from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.core.security import decode_token
from app.modules.users.public import get_auth_state

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: str


async def resolve_user(token: str) -> CurrentUser:
    """Valida el token y consulta rol y estado actuales, para que una suspensión aplique de inmediato."""
    claims = decode_token(token)
    if claims.get("scope"):
        raise AppError(401, "invalid_token", "La sesión no es válida o ya venció")
    state = await get_auth_state(UUID(claims["sub"]))
    if state is None or state.status != "active":
        raise AppError(401, "invalid_token", "La sesión no es válida o ya venció")
    return CurrentUser(id=state.id, role=state.role)


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if credentials is None:
        raise AppError(401, "not_authenticated", "Inicia sesión para continuar")
    return await resolve_user(credentials.credentials)


def require_role(*roles: str) -> Callable[..., Awaitable[CurrentUser]]:
    async def dependency(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise AppError(403, "forbidden", "No tienes permiso para esta acción")
        return user

    return dependency
