"""Autenticación del servicio: el estado de cada usuario sale de la base propia, sin llamadas de red."""
from meloxo_common.auth import build_auth
from meloxo_common.contracts import AuthState

from users_playlists.modules.users import public


async def fetch_auth_state(user_id) -> AuthState | None:
    state = await public.get_auth_state(user_id)
    return AuthState(id=state.id, role=state.role, status=state.status) if state else None


auth = build_auth(fetch_auth_state, ttl=0)  # lectura en proceso: sin caché, un cambio de estado vale al instante
current_user = auth.current_user
require_role = auth.require_role
