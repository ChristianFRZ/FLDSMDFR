import importlib
import pkgutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

import app.modules
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def load_models() -> None:
    """Importa los modelos de cada módulo para registrar sus tablas."""
    for info in pkgutil.iter_modules(app.modules.__path__):
        name = f"app.modules.{info.name}.models"
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name:
                raise


# Solo el comando administrativo de semilla selecciona una base distinta a la del proceso.
maintenance_database = ContextVar("maintenance_database", default=None)


@lru_cache
def _engine(url: str) -> AsyncEngine:
    if get_settings().SERVICE_NAME == "monolith":
        return create_async_engine(url, pool_size=20, max_overflow=40)
    return create_async_engine(url, pool_size=8, max_overflow=12)


def get_engine() -> AsyncEngine:
    return _engine(maintenance_database.get() or get_settings().DATABASE_URL)


def _sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI. Los servicios hacen commit de forma explícita."""
    async with _sessionmaker()() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Sesión propia con commit al salir. La usan las funciones de public.py."""
    async with _sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
