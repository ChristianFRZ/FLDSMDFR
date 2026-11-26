import asyncio
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_DB = "users_playlists_test"


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
os.environ["DISABLE_SCHEDULER"] = "1"
os.environ["REDIS_URL"] = ""  # sin Redis real: el fixture fake_redis instala fakeredis
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""
os.environ["CATALOG_URL"] = "http://catalog.test"  # el mismo que usa tests/fake_catalog.py

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
import respx  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from argon2 import PasswordHasher  # noqa: E402

from meloxo_common.db import Base, get_engine, load_models  # noqa: E402

from tests.fake_catalog import FakeCatalog  # noqa: E402
from users_playlists import security  # noqa: E402
from users_playlists.main import create_app  # noqa: E402
from users_playlists.modules.users.service import login_limiter  # noqa: E402


security._hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)  # hash barato solo en pruebas


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
    load_models("users_playlists.modules")


@pytest.fixture(autouse=True)
async def fake_catalog():
    with respx.mock:
        yield FakeCatalog(respx)


@pytest.fixture(autouse=True)
async def fake_redis():
    from fakeredis import aioredis as fakeredis

    from meloxo_common import revocation
    from meloxo_common.redis_client import override_redis

    client = fakeredis.FakeRedis(decode_responses=True)
    override_redis(client)
    revocation._skip_until = 0.0
    yield client
    override_redis(None)
    revocation._skip_until = 0.0


@pytest.fixture(autouse=True)
async def db_clean():
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        async with get_engine().begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    login_limiter._failures.clear()
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

    def __init__(self, id, email, token, password):
        self.id = id
        self.email = email
        self.token = token
        self.password = password
        self.headers = {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(client):
    counter = iter(range(1, 100_000))

    async def _make(role="listener", email=None, password="secreto123"):
        email = email or f"user{next(counter)}@example.com"
        r = await client.post(
            "/api/auth/register", json={"email": email, "password": password, "display_name": email.split("@")[0]}
        )
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        me = (await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})).json()
        if role != "listener":
            async with get_engine().begin() as conn:
                await conn.execute(text("UPDATE users SET role=:r WHERE id=:i"), {"r": role, "i": me["id"]})
        return TestUser(me["id"], email, token, password)

    return _make


@pytest.fixture
def relogin(client):
    """Token nuevo de alguien cuya sesión fue revocada (cambio de rol o suspensión)."""

    async def _relogin(user):
        r = await client.post("/api/auth/login", json={"email": user.email, "password": user.password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _relogin


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
    """Crea la pista en el catálogo simulado. Si es local y está publicada, también guarda su `track_published`,
    como si el relevo y el consumidor ya lo hubieran movido: así los avisos la ven."""
    from sqlalchemy.dialects.postgresql import insert

    from meloxo_common.db import session_scope
    from tests.fake_catalog import _summary
    from users_playlists.modules.social.models import ReleaseEvent

    async def _make(**kw):
        song = fake_catalog.add_song(**kw)
        if song.status == "published" and song.source == "local" and song.published_at is not None:
            statement = insert(ReleaseEvent).values(
                song_id=song.id, artist_id=song.artist_id, published_at=song.published_at, song=_summary(song)
            )
            async with session_scope() as session:
                await session.execute(statement.on_conflict_do_nothing())
        return song

    return _make


@pytest.fixture(autouse=True)
def fast_resilience(monkeypatch):
    """Sin espera entre reintentos y sin un breaker abierto heredado de otra prueba."""
    from meloxo_common import internal

    monkeypatch.setattr(internal, "RETRY_DELAYS", (0, 0))
    internal.reset_all_breakers()
    yield
    internal.reset_all_breakers()
