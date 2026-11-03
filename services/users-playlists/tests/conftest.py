import asyncio
import os
import tempfile
from pathlib import Path

# Los env de prueba se fijan ANTES de importar `app`.
os.environ.setdefault(
    "FLDSMDFR_DATABASE_URL",
    "postgresql+asyncpg://fldsmdfr:fldsmdfr@db:5432/users_playlists_test",
)
os.environ.setdefault("FLDSMDFR_JWT_SECRET", "secreto-de-pruebas-con-longitud-suficiente-32b")
os.environ.setdefault("FLDSMDFR_ADMIN_EMAIL", "admin@test.mx")
os.environ.setdefault("FLDSMDFR_ADMIN_PASSWORD", "admin12345")
os.environ.setdefault("FLDSMDFR_LISTENER_EMAIL", "oyente@test.mx")
os.environ.setdefault("FLDSMDFR_LISTENER_PASSWORD", "oyente12345")
_MEDIA_TMP = tempfile.TemporaryDirectory(prefix="fldsmdfr-media-")
os.environ["FLDSMDFR_MEDIA_DIR"] = _MEDIA_TMP.name
os.environ["FLDSMDFR_CATALOG_URL"] = "http://catalog.test"

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.db.models_registry  # noqa: E402, F401
from app.clients import http as remote  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.fake_catalog import FakeCatalog  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def media_dir() -> Path:
    return Path(_MEDIA_TMP.name)


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
    """Cada prueba arranca con un catálogo falso vacío en lugar de catalog-streaming."""
    fake = FakeCatalog()
    remote.set_transport("http://catalog.test", httpx.ASGITransport(app=fake.app))
    FakeCatalog.current = fake
    yield fake
    remote.set_transport("http://catalog.test", None)


class _Down(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("catalog-streaming no responde", request=request)


@pytest.fixture
def catalog_down(catalog) -> None:
    """Simula `docker compose stop catalog-streaming`."""
    remote.set_transport("http://catalog.test", _Down())


@pytest.fixture
def catalog_down_later(catalog):
    """Para apagar el catálogo a mitad de la prueba, después de preparar los datos."""
    return lambda: remote.set_transport("http://catalog.test", _Down())
