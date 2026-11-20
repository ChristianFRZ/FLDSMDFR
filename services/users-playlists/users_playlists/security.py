"""Contraseñas (argon2), tokens de acceso y tokens opacos. El JWT en sí vive en `meloxo_common.security`."""
import hashlib
import secrets
from datetime import timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from meloxo_common.security import encode_token

ACCESS_MINUTES = 15
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: UUID | str, role: str) -> str:
    return encode_token({"sub": str(user_id), "role": role}, timedelta(minutes=ACCESS_MINUTES))


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
