"""Importación por lote desde Jamendo: idempotente por jamendo_id y reanudable por offset."""
import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.core.errors import AppError
from app.modules.catalog.jamendo import MAX_PAGE, JamendoClient, JamendoError, JamendoTrack
from app.modules.catalog.models import Album, Artist, ImportJob, Song

log = logging.getLogger(__name__)
BACKOFF_SECONDS = (1, 2, 4)
UPSERT_ROWS = 500  # PostgreSQL admite 32767 parámetros por sentencia y cada fila usa 19
EMPTY_ATTEMPTS = 6
EMPTY_WAIT_SECONDS = 1
STALE_AFTER = timedelta(minutes=10)
background_tasks: set[asyncio.Task] = set()
_sleep = asyncio.sleep
METADATA_FIELDS = (
    "title",
    "duration",
    "genres",
    "tags",
    "license",
    "license_url",
    "jamendo_url",
    "audio_url",
    "cover_url",
)


def spawn(coro: Coroutine) -> None:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)


async def create_job(created_by: UUID | None, params: dict) -> UUID:
    async with session_scope() as session:
        job = ImportJob(params=params, created_by=created_by)
        session.add(job)
        await session.flush()
        return job.id


async def get_job(job_id: UUID) -> ImportJob:
    async with session_scope() as session:
        job = await session.get(ImportJob, job_id)
    if job is None:
        raise AppError(404, "job_not_found", "Importación no encontrada")
    return job


async def list_jobs(limit: int = 20) -> list[ImportJob]:
    async with session_scope() as session:
        query = select(ImportJob).order_by(ImportJob.created_at.desc()).limit(limit)
        return list((await session.execute(query)).scalars())


async def _upsert_artists(session, tracks: list[JamendoTrack]) -> dict[str, UUID]:
    rows = {t.artist_id: {"name": t.artist_name, "source": "jamendo", "jamendo_id": t.artist_id} for t in tracks}
    statement = insert(Artist).values(list(rows.values()))
    statement = statement.on_conflict_do_update(index_elements=["jamendo_id"], set_={"name": statement.excluded.name})
    result = await session.execute(statement.returning(Artist.jamendo_id, Artist.id))
    return dict(result.all())


async def _upsert_albums(session, tracks: list[JamendoTrack], artists: dict[str, UUID]) -> dict[str, UUID]:
    rows = {
        t.album_id: {
            "title": t.album_name or "Sin álbum",
            "artist_id": artists[t.artist_id],
            "jamendo_id": t.album_id,
            "cover_url": t.cover_url,
        }
        for t in tracks
        if t.album_id
    }
    if not rows:
        return {}
    statement = insert(Album).values(list(rows.values()))
    statement = statement.on_conflict_do_update(
        index_elements=["jamendo_id"], set_={"title": statement.excluded.title, "cover_url": statement.excluded.cover_url}
    )
    result = await session.execute(statement.returning(Album.jamendo_id, Album.id))
    return dict(result.all())


def _song_values(track: JamendoTrack) -> dict:
    return {
        "title": track.title,
        "duration": track.duration,
        "genres": track.genres,
        "tags": track.tags,
        "license": track.license,
        "license_url": track.license_url,
        "jamendo_url": track.share_url,
        "audio_url": track.audio_url,
        "cover_url": track.cover_url,
    }


async def _upsert_batch(session: AsyncSession, tracks: list[JamendoTrack], now: datetime) -> None:
    artists = await _upsert_artists(session, tracks)
    albums = await _upsert_albums(session, tracks, artists)
    rows = [
        {
            **_song_values(t),
            "jamendo_id": t.jamendo_id,
            "artist_id": artists[t.artist_id],
            "album_id": albums.get(t.album_id),
            "source": "jamendo",
            "status": "published",
            "published_at": now,
            "imported_at": now,
        }
        for t in tracks
    ]
    statement = insert(Song).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=["jamendo_id"], set_={name: statement.excluded[name] for name in METADATA_FIELDS}
    )
    await session.execute(statement)


async def upsert_tracks(tracks: list[JamendoTrack]) -> None:
    if not tracks:
        return
    unique = list({t.jamendo_id: t for t in tracks}.values())
    now = datetime.now(UTC)
    async with session_scope() as session:
        for start in range(0, len(unique), UPSERT_ROWS):
            await _upsert_batch(session, unique[start : start + UPSERT_ROWS], now)


async def _save(job_id: UUID, **values) -> None:
    async with session_scope() as session:
        await session.execute(
            update(ImportJob).where(ImportJob.id == job_id).values(updated_at=datetime.now(UTC), **values)
        )


async def _fetch_with_backoff(client: JamendoClient, genre: str | None, limit: int, offset: int, order: str):
    for wait in (*BACKOFF_SECONDS, None):
        try:
            return await client.fetch_tracks(genre, limit, offset, order)
        except JamendoError as exc:
            if wait is None or not exc.retryable:
                raise
            await _sleep(wait)
    raise AssertionError("inalcanzable")


async def _fetch_page(client: JamendoClient, genre: str | None, limit: int, offset: int, order: str):
    """Jamendo a veces devuelve una lista vacía para una consulta que sí tiene pistas, así que se pregunta de nuevo."""
    for attempt in range(1, EMPTY_ATTEMPTS + 1):
        tracks = await _fetch_with_backoff(client, genre, limit, offset, order)
        if tracks or attempt == EMPTY_ATTEMPTS:
            return tracks
        await _sleep(EMPTY_WAIT_SECONDS)
    raise AssertionError("inalcanzable")


async def run_import_job(job_id: UUID) -> None:
    job = await get_job(job_id)
    params = job.params
    genres: list[str | None] = list(params.get("genres") or []) or [None]
    limit = int(params.get("limit_per_genre", 200))
    page_size = min(int(params.get("page_size", MAX_PAGE)), MAX_PAGE)
    order = params.get("order", "popularity_total")
    client = JamendoClient()
    imported, genre_index, offset = job.imported, job.genre_index, job.offset
    await _save(job_id, status="running", error=None, started_at=job.started_at or datetime.now(UTC))
    try:
        while genre_index < len(genres):
            remaining = limit - offset
            tracks = []
            if remaining > 0:
                tracks = await _fetch_page(client, genres[genre_index], min(page_size, remaining), offset, order)
            if tracks:
                await upsert_tracks(tracks)
                offset += len(tracks)
                imported += len(tracks)
                await _save(job_id, offset=offset, imported=imported)
            if not tracks or offset >= limit:
                genre_index += 1
                offset = 0
                await _save(job_id, genre_index=genre_index, offset=0)
    except JamendoError as exc:
        await _save(job_id, status="failed", error=str(exc))
        return
    await _save(job_id, status="done", finished_at=datetime.now(UTC))


async def resume_job(job_id: UUID) -> ImportJob:
    job = await get_job(job_id)
    stale = job.status == "running" and datetime.now(UTC) - job.updated_at > STALE_AFTER
    if job.status != "failed" and not stale:
        raise AppError(409, "job_not_resumable", "Esta importación no se puede reanudar")
    spawn(run_import_job(job_id))
    return job


async def refresh_metadata() -> int:
    """Refresco diario: solo actualiza metadatos que cambiaron. Si Jamendo no responde, no hace nada."""
    async with session_scope() as session:
        rows = (await session.execute(select(Song).where(Song.source == "jamendo"))).unique().scalars().all()
        current = {s.jamendo_id: {name: getattr(s, name) for name in METADATA_FIELDS} for s in rows}
    client = JamendoClient()
    ids = list(current)
    changed = []
    try:
        for start in range(0, len(ids), MAX_PAGE):
            for track in await client.fetch_by_ids(ids[start : start + MAX_PAGE]):
                if current.get(track.jamendo_id) != _song_values(track):
                    changed.append(track)
    except JamendoError as exc:
        log.warning("Refresco de Jamendo omitido: %s", exc)
        return 0
    await upsert_tracks(changed)
    return len(changed)
