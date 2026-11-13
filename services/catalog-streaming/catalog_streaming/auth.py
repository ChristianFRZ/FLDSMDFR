"""Autenticación del servicio: el rol y el estado de cada usuario vienen de users-playlists, con caché de 30 s."""
from meloxo_common.auth import Auth, AuthStateCache, build_auth  # noqa: F401

from catalog_streaming.clients.users import get_auth_state

auth_state_cache = AuthStateCache(get_auth_state)
auth = Auth(auth_state_cache)
