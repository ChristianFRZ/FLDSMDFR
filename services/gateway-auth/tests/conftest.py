import os

os.environ["JWT_SECRET"] = "secreto-de-pruebas-con-longitud-suficiente-para-hs256"
os.environ["REDIS_URL"] = ""  # sin Redis real
os.environ["USERS_URL"] = "http://users.test"  # el mismo que usa tests/fake_users.py
# DATABASE_URL no se fija: este servicio no tiene base de datos.

from datetime import timedelta  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
import respx  # noqa: E402

from gateway_auth import auth as service_auth  # noqa: E402
from gateway_auth.main import create_app  # noqa: E402
from meloxo_common.security import encode_token  # noqa: E402
from tests.fake_users import FakeUsers  # noqa: E402


@pytest.fixture(autouse=True)
async def fake_users():
    with respx.mock:
        yield FakeUsers(respx)


@pytest.fixture(autouse=True)
def clean_cache():
    service_auth.auth._cache.clear()
    yield


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def make_token(fake_users):
    def _make(role="listener", status="active"):
        user_id = fake_users.add_user(role=role, status=status)
        return str(user_id), encode_token({"sub": str(user_id)}, timedelta(minutes=5))

    return _make


@pytest.fixture(autouse=True)
def fast_resilience(monkeypatch):
    """Sin espera entre reintentos y sin un breaker abierto heredado de otra prueba."""
    from meloxo_common import internal

    monkeypatch.setattr(internal, "RETRY_DELAYS", (0, 0))
    internal.reset_all_breakers()
    yield
    internal.reset_all_breakers()
