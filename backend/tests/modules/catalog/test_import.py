import asyncio

import httpx
import pytest
import respx
from sqlalchemy import func, select

from app.core.db import session_scope
from app.modules.catalog import import_jobs
from app.modules.catalog.import_jobs import create_job, get_job, refresh_metadata, run_import_job, upsert_tracks
from app.modules.catalog.jamendo import to_track
from app.modules.catalog.models import Artist, Song

API = "https://api.jamendo.com/v3.0/tracks/"


def track(i, **kw):
    return {
        "id": str(i),
        "name": f"Pista {i}",
        "duration": 120 + i,
        "artist_id": "7",
        "artist_name": "TriFace",
        "album_name": "Premiers Jets",
        "album_id": "24",
        "license_ccurl": "http://creativecommons.org/licenses/by-nc-sa/2.0/",
        "image": f"https://img.example/{i}.jpg",
        "audio": f"https://audio.example/{i}",
        "shareurl": f"https://www.jamendo.com/track/{i}",
        "musicinfo": {"tags": {"genres": ["rock"], "vartags": ["energetic"]}},
        **kw,
    }


def page(*tracks):
    return httpx.Response(200, json={"headers": {"status": "success"}, "results": list(tracks)})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_):
        return None

    monkeypatch.setattr(import_jobs, "_sleep", instant)


async def count(model):
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def new_job(limit=2, page_size=2):
    return await create_job(None, {"genres": ["rock"], "limit_per_genre": limit, "page_size": page_size})


@respx.mock
async def test_import_maps_all_fields():
    respx.get(API).mock(return_value=page(track(1)))
    await run_import_job(await new_job(limit=1, page_size=1))
    async with session_scope() as session:
        song = (await session.execute(select(Song))).unique().scalar_one()
        assert song.jamendo_id == "1"
        assert song.title == "Pista 1"
        assert song.artist.name == "TriFace"
        assert song.album.title == "Premiers Jets"
        assert song.duration == 121
        assert song.genres == ["rock"]
        assert song.tags == ["energetic"]
        assert song.cover_url == "https://img.example/1.jpg"
        assert song.audio_url == "https://audio.example/1"
        assert song.jamendo_url == "https://www.jamendo.com/track/1"
        assert song.license == "CC BY-NC-SA 2.0"
        assert song.license_url == "http://creativecommons.org/licenses/by-nc-sa/2.0/"
        assert song.source == "jamendo"
        assert song.status == "published"
        assert song.imported_at is not None


@respx.mock
async def test_request_sends_client_id_and_genre():
    route = respx.get(API).mock(return_value=page())
    await run_import_job(await new_job())
    params = route.calls[0].request.url.params
    assert params["client_id"] == "cliente-de-pruebas"
    assert params["tags"] == "rock"


@respx.mock
async def test_import_is_idempotent():
    respx.get(API).mock(return_value=page(track(1), track(2)))
    await run_import_job(await new_job())
    await run_import_job(await new_job())
    assert await count(Song) == 2
    assert await count(Artist) == 1


@respx.mock
async def test_job_pages_until_limit():
    route = respx.get(API).mock(side_effect=[page(track(1), track(2)), page(track(3), track(4))])
    job_id = await new_job(limit=4)
    await run_import_job(job_id)
    assert route.call_count == 2
    job = await get_job(job_id)
    assert job.status == "done"
    assert job.imported == 4


@respx.mock
async def test_job_stops_on_empty_page():
    route = respx.get(API).mock(side_effect=[page(track(1)), *[page()] * import_jobs.EMPTY_ATTEMPTS])
    job_id = await new_job(limit=10, page_size=1)
    await run_import_job(job_id)
    assert route.call_count == 1 + import_jobs.EMPTY_ATTEMPTS
    assert (await get_job(job_id)).status == "done"


@respx.mock
async def test_job_resumes_from_offset():
    route = respx.get(API).mock(
        side_effect=[page(track(1), track(2)), httpx.Response(500), httpx.Response(500), httpx.Response(500),
                     httpx.Response(500), page(track(3), track(4))]
    )
    job_id = await new_job(limit=4)
    await run_import_job(job_id)
    job = await get_job(job_id)
    assert job.status == "failed"
    assert job.offset == 2
    await run_import_job(job_id)
    assert (await get_job(job_id)).status == "done"
    assert route.calls[-1].request.url.params["offset"] == "2"
    assert await count(Song) == 4


@respx.mock
async def test_429_backs_off_and_finishes(monkeypatch):
    waits = []

    async def record(seconds):
        waits.append(seconds)

    monkeypatch.setattr(import_jobs, "_sleep", record)
    respx.get(API).mock(side_effect=[httpx.Response(429), httpx.Response(429), page(track(1), track(2))])
    job_id = await new_job()
    await run_import_job(job_id)
    assert waits == [1, 2]
    assert (await get_job(job_id)).status == "done"


@respx.mock
async def test_jamendo_down_marks_failed():
    respx.get(API).mock(side_effect=httpx.ConnectError("caído"))
    job_id = await new_job()
    await run_import_job(job_id)
    job = await get_job(job_id)
    assert job.status == "failed"
    assert job.error


@respx.mock
async def test_api_level_error_marks_failed():
    bad = httpx.Response(200, json={"headers": {"status": "failed", "error_message": "cuota"}, "results": []})
    respx.get(API).mock(return_value=bad)
    job_id = await new_job()
    await run_import_job(job_id)
    job = await get_job(job_id)
    assert job.status == "failed"
    assert "cuota" in job.error


@respx.mock
async def test_import_route_returns_job_id(client, admin):
    respx.get(API).mock(return_value=page(track(1)))
    r = await client.post(
        "/api/admin/catalog/import", json={"genres": ["rock"], "limit_per_genre": 1}, headers=admin.headers
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    await asyncio.gather(*import_jobs.background_tasks)
    r = await client.get(f"/api/admin/catalog/import/{job_id}", headers=admin.headers)
    assert r.json()["status"] == "done"
    row = (await client.get("/api/admin/audit?action=catalog_import", headers=admin.headers)).json()["items"][0]
    assert row["target_id"] == job_id


async def test_import_403_for_others(client, make_user):
    for role in ("listener", "composer"):
        u = await make_user(role=role)
        r = await client.post("/api/admin/catalog/import", json={"genres": [], "limit_per_genre": 1}, headers=u.headers)
        assert r.status_code == 403


async def test_import_limit_validated(client, admin):
    r = await client.post(
        "/api/admin/catalog/import", json={"genres": ["rock"], "limit_per_genre": 0}, headers=admin.headers
    )
    assert r.status_code == 422


async def test_job_not_found_404(client, admin):
    r = await client.get("/api/admin/catalog/import/00000000-0000-0000-0000-000000000000", headers=admin.headers)
    assert r.status_code == 404


@respx.mock
async def test_import_does_not_block_search(client, admin, listener, make_song):
    await make_song()
    gate = asyncio.Event()

    async def slow(_):
        await gate.wait()
        return page(track(1))

    respx.get(API).mock(side_effect=slow)
    await client.post("/api/admin/catalog/import", json={"genres": ["rock"], "limit_per_genre": 1}, headers=admin.headers)
    r = await client.get("/api/songs", headers=listener.headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    gate.set()
    await asyncio.gather(*import_jobs.background_tasks)


@respx.mock
async def test_refresh_updates_changed_metadata_only():
    respx.get(API).mock(return_value=page(track(1), track(2)))
    await run_import_job(await new_job())
    respx.get(API).mock(return_value=page(track(1, name="Nuevo nombre"), track(2)))
    assert await refresh_metadata() == 1
    async with session_scope() as session:
        titles = sorted((await session.execute(select(Song.title))).scalars())
    assert titles == ["Nuevo nombre", "Pista 2"]


@respx.mock
async def test_refresh_keeps_admin_hidden_songs_hidden():
    respx.get(API).mock(return_value=page(track(1)))
    await run_import_job(await new_job(limit=1, page_size=1))
    async with session_scope() as session:
        song = (await session.execute(select(Song))).unique().scalar_one()
        song.status = "hidden"
    await refresh_metadata()
    async with session_scope() as session:
        assert await session.scalar(select(Song.status)) == "hidden"


@respx.mock
async def test_refresh_survives_jamendo_down():
    respx.get(API).mock(return_value=page(track(1)))
    await run_import_job(await new_job(limit=1, page_size=1))
    respx.get(API).mock(side_effect=httpx.ConnectError("caído"))
    assert await refresh_metadata() == 0


@respx.mock
async def test_empty_page_from_jamendo_is_retried():
    """Jamendo devuelve listas vacías al azar: eso no significa que el género se acabó."""
    route = respx.get(API).mock(side_effect=[page(), page(), page(track(1), track(2))])
    job_id = await create_job(None, {"genres": ["rock"], "limit_per_genre": 2})
    await run_import_job(job_id)
    job = await get_job(job_id)
    assert (job.status, job.imported) == ("done", 2)
    assert route.call_count == 3


@respx.mock
async def test_genre_without_tracks_ends_after_retries():
    route = respx.get(API).mock(return_value=page())
    job_id = await create_job(None, {"genres": ["rock"], "limit_per_genre": 2})
    await run_import_job(job_id)
    assert (await get_job(job_id)).status == "done"
    assert route.call_count == import_jobs.EMPTY_ATTEMPTS


async def test_upsert_more_rows_than_postgres_allows_in_one_statement():
    """Jamendo cambia audio_url en cada consulta: el refresco diario reescribe todo el catálogo."""
    await upsert_tracks([to_track(track(i)) for i in range(1, 1801)])
    async with session_scope() as session:
        assert await session.scalar(select(func.count()).select_from(Song)) == 1800
