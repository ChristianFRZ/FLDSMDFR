"""Cliente de users-playlists (solo lo que necesitan las métricas)."""

from app.clients import http
from app.config import get_settings

SERVICE = "users-playlists"


async def count_users() -> int:
    response = await http.call(SERVICE, get_settings().users_url, "GET", "/internal/users/count")
    return response.json()["count"]
