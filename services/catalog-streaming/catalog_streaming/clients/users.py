"""Llamadas HTTP a users-playlists. Si ese servicio no responde, `UpstreamError` (503)."""
from uuid import UUID

from meloxo_common.contracts import AuditEntry, AuthState
from meloxo_common.errors import AppError
from meloxo_common.internal import BATCH_SIZE, InternalClient

from catalog_streaming.config import get_settings

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


async def get_display_names(ids: list[UUID]) -> dict[UUID, str]:
    if not ids:
        return {}
    names: dict[UUID, str] = {}
    for start in range(0, len(ids), BATCH_SIZE):
        batch = ",".join(str(i) for i in ids[start : start + BATCH_SIZE])
        found = await _users().get("/internal/users/display-names", ids=batch)
        names.update({UUID(key): value for key, value in found.items()})
    return names


async def record_audit(entry: AuditEntry) -> None:
    await _users().post("/internal/audit", json=entry.model_dump(mode="json"))
