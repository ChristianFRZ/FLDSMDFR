import asyncio
import os
from pathlib import Path

# Los env de prueba se fijan ANTES de importar `app`.
os.environ.setdefault(
    "FLDSMDFR_DATABASE_URL",
    "postgresql+asyncpg://fldsmdfr:fldsmdfr@db:5432/playback_test",
)
os.environ.setdefault("FLDSMDFR_JWT_SECRET", "secreto-de-pruebas-con-longitud-suficiente-32b")

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.modules.playback.models  # noqa: E402, F401
from app.clients import http as remote  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.fake_catalog import FakeCatalog  # noqa: E402
from tests.fake_users import FakeUsers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def media_dir(tmp_path) -> Path:
    """Compatibilidad con las pruebas heredadas; este servicio no guarda archivos."""
    return tmp_path


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _migrate() -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "app/db/migrations"))
    # env.py usa asyncio.run: se ejecuta en un hilo aparte del loop de pruebas.
    await asyncio.to_thread(command.upgrade, cfg, "head")


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(_migrate) -> None:
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if tables:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def catalog() -> FakeCatalog:
    fake = FakeCatalog()
    remote.set_transport("catalog-streaming", httpx.ASGITransport(app=fake.app))
    FakeCatalog.current = fake
    yield fake
    remote.set_transport("catalog-streaming", None)


@pytest.fixture(autouse=True)
def users() -> FakeUsers:
    fake = FakeUsers()
    remote.set_transport("users-playlists", httpx.ASGITransport(app=fake.app))
    yield fake
    remote.set_transport("users-playlists", None)


class _Down(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("servicio caído", request=request)


@pytest.fixture
def take_down(catalog, users):
    """take_down("catalog-streaming") simula `docker compose stop` de ese servicio."""
    return lambda base_url: remote.set_transport(base_url, _Down())
