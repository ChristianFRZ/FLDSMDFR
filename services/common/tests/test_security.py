from datetime import timedelta

import jwt
import pytest

from meloxo_common.config import BaseServiceSettings, get_base_settings
from meloxo_common.errors import AppError
from meloxo_common.security import decode_token, encode_token


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x/y")
    monkeypatch.setenv("JWT_SECRET", "secreto-de-prueba-de-32-bytes-o-mas-xx")
    get_base_settings.cache_clear()
    yield
    get_base_settings.cache_clear()


def test_roundtrip_keeps_claims():
    token = encode_token({"sub": "u1", "role": "listener"}, timedelta(minutes=5))
    claims = decode_token(token)
    assert claims["sub"] == "u1" and claims["role"] == "listener" and "exp" in claims


def test_expired_token_is_invalid():
    with pytest.raises(AppError) as exc:
        decode_token(encode_token({"sub": "u1"}, timedelta(seconds=-5)))
    assert (exc.value.status, exc.value.code) == (401, "invalid_token")


def test_wrong_secret_is_invalid():
    bad = jwt.encode({"sub": "u1"}, "otro-secreto-de-prueba-de-32-bytes-xx", algorithm="HS256")
    with pytest.raises(AppError):
        decode_token(bad)


def test_settings_defaults():
    s = BaseServiceSettings()
    assert (s.DISABLE_SCHEDULER, s.INTERNAL_TIMEOUT_SECONDS, s.AUTH_CACHE_SECONDS) == (False, 3.0, 30)


@pytest.mark.parametrize("secret", ["", "corto", "x" * 31])
def test_short_or_empty_jwt_secret_is_rejected(monkeypatch, secret):
    monkeypatch.setenv("JWT_SECRET", secret)
    with pytest.raises(ValueError):
        BaseServiceSettings()


def test_jwt_secret_of_32_chars_is_accepted(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    assert BaseServiceSettings().JWT_SECRET == "x" * 32
