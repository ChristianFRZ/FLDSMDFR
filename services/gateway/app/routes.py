"""Tabla de rutas del gateway: qué servicio lógico atiende cada prefijo público.

Es la misma tabla que el nginx.conf de 02-separacion. El orden importa: gana el prefijo más
específico (por eso /api/me/history va antes que el resto de /api).
"""

BLOCKED = object()  # /internal: la API entre servicios no se expone

_PREFIXES: list[tuple[str, str]] = [
    ("/api/playbacks", "playback-metrics"),
    ("/api/metrics/", "playback-metrics"),
    ("/api/me/history", "playback-metrics"),
    ("/api/songs", "catalog-streaming"),
    ("/api/", "users-playlists"),  # auth, users, playlists, invites y el resto de /api/me/
]


def service_for(path: str) -> str | object:
    """Nombre lógico del servicio para `path` (ya decodificado), o BLOCKED.

    Lo que no es /api va al SPA (web). Una ruta con segmentos `.` o `..` se bloquea: httpx los
    resuelve al reenviar, así que `/api/../internal/...` llegaría a /internal. Los navegadores ya
    los quitan antes de enviar, de modo que solo los manda quien busca saltarse esta tabla.
    """
    if any(segment in (".", "..") for segment in path.split("/")):
        return BLOCKED
    if path == "/internal" or path.startswith("/internal/"):
        return BLOCKED
    for prefix, service in _PREFIXES:
        if path.startswith(prefix):
            return service
    return "web"
