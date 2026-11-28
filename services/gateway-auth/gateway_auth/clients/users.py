"""Llamada HTTP a users-playlists. Si ese servicio no responde, `UpstreamError` (503)."""
from uuid import UUID

from meloxo_common.contracts import AuthState
from meloxo_common.errors import AppError
from meloxo_common.internal import InternalClient

# Import relativo a propósito: el detector de fronteras trata `clients/` como un módulo y
# marcaría `gateway_auth.config`; este servicio es plano y `config` es compartido.
from ..config import get_settings

_client: InternalClient | None = None
_client_url: str | None = None


def _users() -> InternalClient:
    """Un cliente por URL: se vuelve a crear si cambia `USERS_URL`."""
    global _client, _client_url
    settings = get_settings()
    if _client is None or _client_url != settings.USERS_URL:
        _client = InternalClient(settings.USERS_URL, timeout=settings.INTERNAL_TIMEOUT_SECONDS)
        _client_url = settings.USERS_URL
    return _client


async def get_auth_state(user_id: UUID) -> AuthState | None:
    """Un 404 significa que el usuario no existe."""
    try:
        data = await _users().get(f"/internal/users/{user_id}/auth-state")
    except AppError as exc:
        if exc.status == 404:
            return None
        raise
    return AuthState.model_validate(data)
