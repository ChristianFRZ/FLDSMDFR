import importlib
import pkgutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from meloxo_common.config import get_base_settings


class Base(DeclarativeBase):
    pass


def load_models(package: str) -> None:
    """Importa `<package>.<submódulo>.models` de cada módulo para registrar sus tablas."""
    pkg = importlib.import_module(package)
    for info in pkgutil.iter_modules(pkg.__path__):
        name = f"{package}.{info.name}.models"
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name:
                raise


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_base_settings().DATABASE_URL, pool_size=20, max_overflow=40)


@lru_cache
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
