"""Cliente de users-playlists (solo lo que necesitan las métricas)."""

from app.clients import http

SERVICE = "users-playlists"


async def count_users() -> int:
    response = await http.call(SERVICE, "GET", "/internal/users/count")
    return response.json()["count"]
