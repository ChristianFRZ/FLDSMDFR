import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db import Base, load_models

load_models()
target_metadata = Base.metadata


DOMAIN_MODULES = {
    "users_playlists": {"users", "playlists", "social"},
    "catalog": {"catalog"},
    "playbacks": {"playback", "analytics"},
}
domain = context.config.attributes.get("domain")
owned_tables = {
    mapper.local_table.name for mapper in Base.registry.mappers
    if not domain or mapper.class_.__module__.split(".")[2] in DOMAIN_MODULES[domain]
}


def include_object(obj, name, kind, reflected, compare_to):
    if kind == "table":
        return name in owned_tables
    return True


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


async def main():
    engine = create_async_engine(get_settings().DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(run)
        await connection.commit()
    await engine.dispose()


asyncio.run(main())
