import asyncio
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_DB = "meloxo_test"


def _postgres_password() -> str:
    """La misma clave que usa docker compose: nunca escrita en un archivo versionado."""
    if password := os.environ.get("POSTGRES_PASSWORD"):
        return password
    for line in (ROOT.parent / ".env").read_text().splitlines():
        if line.startswith("POSTGRES_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Falta POSTGRES_PASSWORD en .env")


_base = f"postgresql+asyncpg://meloxo:{_postgres_password()}@localhost:5433"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"{_base}/{TEST_DB}")
os.environ["JWT_SECRET"] = "secreto-de-pruebas-con-longitud-suficiente-para-hs256"
os.environ["DISABLE_SCHEDULER"] = "1"
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="meloxo-media-")
os.environ["ADMIN_EMAIL"] = ""
os.environ["ADMIN_PASSWORD"] = ""
os.environ["JAMENDO_CLIENT_ID"] = "cliente-de-pruebas"

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from argon2 import PasswordHasher  # noqa: E402

from app.core import security  # noqa: E402
from app.core.db import Base, get_engine, load_models, session_scope  # noqa: E402
from app.main import create_app
from app.modules.catalog import public as catalog_public  # noqa: E402
from app.modules.users.service import login_limiter  # noqa: E402


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
    load_models()


@pytest.fixture(autouse=True)
async def db_clean():
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        async with get_engine().begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    login_limiter._failures.clear()
    catalog_public._jamendo_status.clear()
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
    from app.modules.catalog.models import Album, Artist, Song

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
