import asyncio
import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
TEST_DB = "catalog_test"
USERS_URL = "http://users.test"


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
os.environ["CACHE_REDIS_URL"] = ""  # sin caché real: las pruebas instalan fakeredis con override_cache
os.environ["DISABLE_SCHEDULER"] = "1"
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="meloxo-media-")
os.environ["JAMENDO_CLIENT_ID"] = "cliente-de-pruebas"
os.environ["USERS_URL"] = USERS_URL

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
import respx  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from meloxo_common.db import Base, get_engine, load_models, session_scope  # noqa: E402
from meloxo_common.security import encode_token  # noqa: E402

from catalog_streaming.auth import auth_state_cache  # noqa: E402
from catalog_streaming.main import create_app  # noqa: E402
from catalog_streaming.modules.catalog import public as catalog_public  # noqa: E402


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
    load_models("catalog_streaming.modules")


class TestUser:
    __test__ = False

    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role
        self.token = encode_token({"sub": id}, timedelta(hours=1))
        self.headers = {"Authorization": f"Bearer {self.token}"}


class UsersService:
    """Simula users-playlists con respx: estado de autenticación, nombres y auditoría."""

    def __init__(self, router):
        self.users: dict[str, TestUser] = {}
        self.statuses: dict[str, str] = {}
        self.audits: list[dict] = []
        self.audit_down = False
        self.down = False
        router.get(url__regex=rf"{USERS_URL}/internal/users/(?P<user_id>[^/]+)/auth-state", name="users_auth").mock(side_effect=self._auth)
        router.get(f"{USERS_URL}/internal/users/display-names", name="users_names").mock(side_effect=self._names)
        router.post(f"{USERS_URL}/internal/audit", name="users_audit").mock(side_effect=self._audit)

    def add(self, role: str, email: str) -> TestUser:
        user = TestUser(str(uuid4()), email, role)
        self.users[user.id] = user
        self.statuses[user.id] = "active"
        return user

    def set_status(self, user: TestUser, status: str) -> None:
        """El estado cambia en users-playlists; el servicio lo ve cuando vence su caché."""
        self.statuses[user.id] = status
        auth_state_cache.clear()

    def _auth(self, request, user_id):
        if self.down:
            raise httpx.ConnectError("users caído")
        user = self.users.get(user_id)
        if user is None:
            return httpx.Response(404, json={"error": {"code": "user_not_found", "message": "No existe"}})
        return httpx.Response(200, json={"id": user.id, "role": user.role, "status": self.statuses[user.id]})

    def _names(self, request):
        if self.down:
            raise httpx.ConnectError("users caído")
        ids = request.url.params["ids"].split(",")
        return httpx.Response(
            200, json={i: self.users[i].email.split("@")[0] for i in ids if i in self.users}
        )

    def _audit(self, request):
        if self.down or self.audit_down:
            raise httpx.ConnectError("users caído")
        self.audits.append(json.loads(request.content))
        return httpx.Response(204)


@pytest.fixture(autouse=True)
async def users_service():
    with respx.mock:
        yield UsersService(respx)
        for name in ("users_auth", "users_names", "users_audit"):
            respx.mock.routes.pop(name, None)  # no todas las pruebas las usan


@pytest.fixture(autouse=True)
async def db_clean():
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        async with get_engine().begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    catalog_public._jamendo_status.clear()
    auth_state_cache.clear()
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def make_user(users_service):
    counter = iter(range(1, 100_000))

    async def _make(role="listener", email=None):
        return users_service.add(role, email or f"user{next(counter)}@example.com")

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
def make_song():
    from catalog_streaming.modules.catalog.models import Album, Artist, Song

    async def _make(
        title="Luz de carretera",
        artist="Marea Baja",
        album="Noches",
        source="local",
        status="published",
        genres=("rock",),
        tags=("guitarra",),
        owner=None,
        **kw,
    ):
        async with session_scope() as session:
            found = (await session.execute(select(Artist).where(Artist.name == artist))).scalar_one_or_none()
            if found is None:
                found = Artist(name=artist, source=source, owner_user_id=owner)
                session.add(found)
                await session.flush()
            record = Album(title=album, artist_id=found.id)
            session.add(record)
            await session.flush()
            song = Song(
                title=title,
                artist_id=found.id,
                album_id=record.id,
                duration=kw.pop("duration", 180),
                genres=list(genres),
                tags=list(tags),
                source=source,
                license=kw.pop("license", "CC BY-NC-SA"),
                status=status,
                **kw,
            )
            session.add(song)
            await session.flush()
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


@pytest.fixture
async def fake_redis():
    from fakeredis import aioredis as fakeredis

    from meloxo_common.redis_client import override_redis

    client = fakeredis.FakeRedis(decode_responses=True)
    override_redis(client)
    yield client
    override_redis(None)
