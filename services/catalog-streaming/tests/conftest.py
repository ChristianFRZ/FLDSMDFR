import asyncio
import os
import tempfile
from pathlib import Path

# Los env de prueba se fijan ANTES de importar `app`.
os.environ.setdefault(
    "FLDSMDFR_DATABASE_URL",
    "postgresql+asyncpg://fldsmdfr:fldsmdfr@db:5432/catalog_test",
)
os.environ.setdefault("FLDSMDFR_JWT_SECRET", "secreto-de-pruebas-con-longitud-suficiente-32b")
_MEDIA_TMP = tempfile.TemporaryDirectory(prefix="fldsmdfr-media-")
os.environ["FLDSMDFR_MEDIA_DIR"] = _MEDIA_TMP.name

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.modules.catalog.models  # noqa: E402, F401
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

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
