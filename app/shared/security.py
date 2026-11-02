"""Hash de contrasenas (Argon2) y tokens JWT de sesion."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.config import get_settings
from app.shared.errors import Unauthorized

_ALGORITHM = "HS256"
_hasher = PasswordHash.recommended()


@dataclass(frozen=True)
class TokenData:
    user_id: UUID
    role: str


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _hasher.verify(plain, hashed)


def create_access_token(user_id: UUID, role: str) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    claims = {"sub": str(user_id), "role": role, "exp": expires}
    return jwt.encode(claims, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "role", "exp"]},
        )
        return TokenData(user_id=UUID(claims["sub"]), role=str(claims["role"]))
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise Unauthorized("Tu sesión expiró o no es válida.") from exc
