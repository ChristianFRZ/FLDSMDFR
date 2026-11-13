"""Llamadas HTTP a users-playlists. Si ese servicio no responde, `UpstreamError` (503)."""
from uuid import UUID

from meloxo_common.contracts import AuthState, TapeActivity, UserGrowthPoint
from meloxo_common.errors import AppError
from meloxo_common.internal import BATCH_SIZE, InternalClient

from playback_metrics.config import get_settings

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


async def user_growth(days: int) -> list[UserGrowthPoint]:
    return [UserGrowthPoint.model_validate(p) for p in await _users().get("/internal/users/growth", days=days)]


async def _count(path: str, song_ids: list[UUID]) -> int:
    """Una llamada por cada 200 pistas. Con 200 o menos el conteo es exacto.

    Con más, se suman los conteos de cada lote: una playlist (o casete) con pistas de dos lotes se cuenta dos veces,
    así que el resultado es una cota superior. Nunca queda por debajo del valor real.
    """
    ids = list(dict.fromkeys(song_ids))
    total = 0
    for start in range(0, len(ids), BATCH_SIZE):
        batch = ",".join(str(i) for i in ids[start : start + BATCH_SIZE])
        total += (await _users().get(path, song_ids=batch))["count"]
    return total


async def count_inclusions(song_ids: list[UUID]) -> int:
    return await _count("/internal/playlists/inclusions", song_ids)


async def count_tape_inclusions(song_ids: list[UUID]) -> int:
    return await _count("/internal/tapes/inclusions", song_ids)


async def tape_activity() -> TapeActivity:
    return TapeActivity.model_validate(await _users().get("/internal/tapes/activity"))
