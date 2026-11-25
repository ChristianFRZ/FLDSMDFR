"""Autenticación del servicio: el rol y el estado de cada usuario vienen de users-playlists, con caché de 30 s."""
from meloxo_common.auth import build_auth

from playback_metrics.clients.users import get_auth_state

auth = build_auth(get_auth_state)
current_user = auth.current_user
require_role = auth.require_role
