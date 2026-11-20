import asyncio
from uuid import UUID, uuid4

from sqlalchemy import func, select

from meloxo_common.db import session_scope

from catalog_streaming.modules.catalog import composer
from catalog_streaming.modules.catalog.models import Artist


async def test_ensure_artist_concurrent_creates_one_artist(make_user, monkeypatch):
    user = await make_user(role="composer", email="nuevo@example.com")

    # Todas las llamadas ven «sin artista» antes de que alguna inserte: el peor orden posible.
    barrier = asyncio.Barrier(10)
    original = composer.get_display_names

    async def synchronized(ids):
        await barrier.wait()
        return await original(ids)

    monkeypatch.setattr(composer, "get_display_names", synchronized)

    async def first_call():
        async with session_scope() as session:
            return (await composer.ensure_artist(session, UUID(user.id))).id

    ids = await asyncio.gather(*(first_call() for _ in range(10)))
    assert len(set(ids)) == 1
    async with session_scope() as session:
        assert await session.scalar(select(func.count()).select_from(Artist)) == 1
        assert await session.scalar(select(Artist.name)) == "nuevo"


async def test_ensure_artist_without_display_name_uses_default(users_service):
    unknown = uuid4()
    async with session_scope() as session:
        artist = await composer.ensure_artist(session, unknown)
    assert artist.name == "Sin nombre"
