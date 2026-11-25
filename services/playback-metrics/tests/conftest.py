import asyncio
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_DB = "playbacks_test"


def _postgres_password() -> str:
    """La misma clave que usa docker compose: nunca escrita en un archivo versionado."""
    if password := os.environ.get("POSTGRES_PASSWORD"):
        return password
    for line in (ROOT.parent.parent / ".env").read_text().splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Falta POSTGRES_PASSWORD en .env")


_base = f"postgresql+asyncpg://meloxo:{_postgres_password()}@localhost:5433"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"{_base}/{TEST_DB}")
os.environ["JWT_SECRET"] = "secreto-de-pruebas-con-longitud-suficiente-para-hs256"
os.environ["REDIS_URL"] = ""  # sin Redis real
os.environ["DISABLE_SCHEDULER"] = "1"
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="meloxo-media-")
os.environ["CATALOG_URL"] = "http://catalog.test"  # el mismo que usa tests/fake_catalog.py
os.environ["USERS_URL"] = "http://users.test"  # el mismo que usa tests/fake_users.py

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
import respx  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from meloxo_common.db import Base, get_engine, load_models  # noqa: E402
from meloxo_common.security import encode_token  # noqa: E402

from datetime import timedelta  # noqa: E402

from playback_metrics import auth as service_auth  # noqa: E402
from playback_metrics.main import create_app  # noqa: E402
from tests.fake_catalog import FakeCatalog  # noqa: E402
from tests.fake_users import FakeUsers  # noqa: E402


async def _ensure_database():
    conn = await asyncpg.connect(
        host="localhost", port=5433, user="meloxo", password=_postgres_password(), database="meloxo"
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", TEST_DB)
        if not exists:
            await conn.execute(f"CREATE DATABASE {TEST_DB}")
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def database():
    asyncio.run(_ensure_database())
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(cfg, "head")
    load_models("playback_metrics.modules")


@pytest.fixture(autouse=True)
async def fake_services():
    with respx.mock:
        yield FakeCatalog(respx), FakeUsers(respx)


@pytest.fixture
def fake_catalog(fake_services):
    return fake_services[0]


@pytest.fixture
def fake_users(fake_services):
    return fake_services[1]


@pytest.fixture(autouse=True)
async def db_clean():
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        async with get_engine().begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    service_auth.auth._cache.clear()
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestUser:
    __test__ = False

    def __init__(self, id, email, token):
        self.id = id
        self.email = email
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(fake_users):
    counter = iter(range(1, 100_000))

    async def _make(role="listener", email=None):
        user_id = fake_users.add_user(role=role)
        token = encode_token({"sub": str(user_id)}, timedelta(minutes=5))
        return TestUser(str(user_id), email or f"user{next(counter)}@example.com", token)

    return _make


@pytest.fixture
async def listener(make_user):
    return await make_user()


@pytest.fixture
async def composer(make_user):
    return await make_user(role="composer")


@pytest.fixture
async def admin(make_user):
    return await make_user(role="admin")


@pytest.fixture
def make_song(fake_catalog):
    async def _make(**kw):
        return fake_catalog.add_song(**kw)

    return _make


@pytest.fixture(autouse=True)
def fast_resilience(monkeypatch):
    """Sin espera entre reintentos y sin un breaker abierto heredado de otra prueba."""
    from meloxo_common import internal

    monkeypatch.setattr(internal, "RETRY_DELAYS", (0, 0))
    internal.reset_all_breakers()
    yield
    internal.reset_all_breakers()


@pytest.fixture
async def fake_redis():
    from fakeredis import aioredis as fakeredis

    from meloxo_common.redis_client import override_redis

    client = fakeredis.FakeRedis(decode_responses=True)
    override_redis(client)
    yield client
    override_redis(None)
