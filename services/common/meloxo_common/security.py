"""JWT compartido. El hash de contraseñas vive en users-playlists."""
import time
from datetime import timedelta

import jwt

from meloxo_common.config import get_base_settings
from meloxo_common.errors import AppError

ALGORITHM = "HS256"


def encode_token(claims: dict, ttl: timedelta) -> str:
    now = time.time()
    payload = {**claims, "iat": now, "exp": int(now + ttl.total_seconds())}
    return jwt.encode(payload, get_base_settings().JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_base_settings().JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError(401, "invalid_token", "La sesión no es válida o ya venció") from exc
