import asyncio

from sqlalchemy import func, select

from meloxo_common.db import session_scope

from catalog_streaming.modules.catalog import import_jobs
from catalog_streaming.modules.catalog.models import ImportJob, Song


async def song_state(song):
    async with session_scope() as session:
        return await session.scalar(select(Song.status).where(Song.id == song.id))


async def job_count():
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(ImportJob))


async def test_hide_song_returns_503_when_audit_unreachable(client, admin, make_song, users_service):
    song = await make_song()
    users_service.audit_down = True
    r = await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "derechos"}, headers=admin.headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "upstream_unavailable"
    assert await song_state(song) == "published"


async def test_restore_and_import_return_503_when_audit_down(client, admin, make_song, users_service):
    song = await make_song()
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    assert await song_state(song) == "hidden"
    users_service.audit_down = True

    r = await client.post(f"/api/admin/songs/{song.id}/restore", headers=admin.headers)
    assert r.status_code == 503
    assert await song_state(song) == "hidden"

    r = await client.post(
        "/api/admin/catalog/import", json={"genres": ["rock"], "limit_per_genre": 1}, headers=admin.headers
    )
    assert r.status_code == 503
    assert await job_count() == 0
    assert not import_jobs.background_tasks
    await asyncio.sleep(0)
