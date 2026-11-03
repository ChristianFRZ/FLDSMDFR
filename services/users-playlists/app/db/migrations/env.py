"""Entorno Alembic asíncrono; la URL sale de Settings y los modelos de models_registry."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import app.db.models_registry  # noqa: F401  (puebla Base.metadata)
from app.config import get_settings
from app.db.base import Base

target_metadata = Base.metadata


def _run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=get_settings().database_url, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_online())
