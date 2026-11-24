import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from meloxo_common.config import get_base_settings
from meloxo_common.db import Base, load_models

load_models("catalog_streaming.modules")
target_metadata = Base.metadata


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def main():
    engine = create_async_engine(get_base_settings().DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(run)
        await connection.commit()
    await engine.dispose()


asyncio.run(main())
