"""Autenticación compartida: valida el JWT y consulta rol y estado con una caché de 30 s."""
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from meloxo_common import revocation
from meloxo_common.contracts import AuthState
from meloxo_common.errors import AppError
from meloxo_common.internal import UpstreamError
from meloxo_common.security import decode_token

_bearer = HTTPBearer(auto_error=False)

FetchAuthState = Callable[[UUID], Awaitable[AuthState | None]]


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: str


class AuthStateCache:
    """Guarda el estado de cada usuario `ttl` segundos. Si el origen cae, usa el último estado sin importar su edad."""

    def __init__(self, fetch: FetchAuthState, ttl: float = 30, clock: Callable[[], float] = time.monotonic):
        self._fetch = fetch
        self._ttl = ttl
        self._clock = clock
        self._entries: dict[UUID, tuple[float, AuthState | None, float]] = {}  # (reloj, estado, hora de pared)

    def clear(self) -> None:
        self._entries.clear()

    async def get(self, user_id: UUID, not_before: float | None = None) -> AuthState | None:
        """`not_before` (hora de pared) descarta lo guardado antes de esa hora: así un cambio de rol ya revocado se ve al instante."""
        entry = self._entries.get(user_id)
        now = self._clock()
        if entry is not None and now - entry[0] < self._ttl and (not_before is None or entry[2] >= not_before):
            return entry[1]
        try:
            state = await self._fetch(user_id)
        except UpstreamError:
            if entry is None:
                raise
            return entry[1]
        self._entries[user_id] = (now, state, time.time())
        return state


class Auth:
    def __init__(self, cache: AuthStateCache):
        self._cache = cache

    async def resolve_user(self, token: str) -> CurrentUser:
        claims = decode_token(token)
        if claims.get("scope"):
            raise AppError(401, "invalid_token", "La sesión no es válida o ya venció")
        user_id = UUID(claims["sub"])
        revoked = await revocation.revoked_after(user_id)
        if revoked is not None and claims.get("iat", 0) < revoked:
            raise AppError(401, "invalid_token", "La sesión no es válida o ya venció")
        state = await self._cache.get(user_id, not_before=revoked)
        if state is None or state.status != "active":
            raise AppError(401, "invalid_token", "La sesión no es válida o ya venció")
        return CurrentUser(id=state.id, role=state.role)

    async def current_user(
        self, credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)
    ) -> CurrentUser:
        if credentials is None:
            raise AppError(401, "not_authenticated", "Inicia sesión para continuar")
        return await self.resolve_user(credentials.credentials)

    def require_role(self, *roles: str) -> Callable[..., Awaitable[CurrentUser]]:
        async def dependency(user: CurrentUser = Depends(self.current_user)) -> CurrentUser:
            if user.role not in roles:
                raise AppError(403, "forbidden", "No tienes permiso para esta acción")
            return user

        return dependency


def build_auth(
    fetch: FetchAuthState, ttl: float = 30, clock: Callable[[], float] = time.monotonic
) -> Auth:
    return Auth(AuthStateCache(fetch, ttl, clock))
