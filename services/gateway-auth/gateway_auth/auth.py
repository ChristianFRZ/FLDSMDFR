"""Autenticación del servicio: rol y estado vienen de users-playlists, con caché."""
from meloxo_common.auth import build_auth

from gateway_auth.clients.users import get_auth_state
from gateway_auth.config import get_settings

auth = build_auth(get_auth_state, ttl=get_settings().AUTH_CACHE_SECONDS)
