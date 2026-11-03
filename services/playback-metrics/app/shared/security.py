"""Validación de los JWT de sesión. Solo users-playlists los emite; aquí solo se decodifican."""

from dataclasses import dataclass
from uuid import UUID

import jwt

from app.config import get_settings
from app.shared.errors import Unauthorized

ALGORITHM = "HS256"


@dataclass(frozen=True)
class TokenData:
    user_id: UUID
    role: str


def decode_access_token(token: str) -> TokenData:
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "role", "exp"]},
        )
        return TokenData(user_id=UUID(claims["sub"]), role=str(claims["role"]))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise Unauthorized("Tu sesión expiró o no es válida.") from exc
