import hashlib
import secrets
import time
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.errors import AppError

ACCESS_MINUTES = 15
ALGORITHM = "HS256"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(claims: dict, seconds: int) -> str:
    payload = {**claims, "exp": int(time.time()) + seconds}
    return jwt.encode(payload, get_settings().JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: UUID | str, role: str) -> str:
    return create_token({"sub": str(user_id), "role": role}, ACCESS_MINUTES * 60)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError(401, "invalid_token", "La sesión no es válida o ya venció") from exc


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
