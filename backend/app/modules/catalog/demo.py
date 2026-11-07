"""Pistas ficticias de la semilla de demo. Las pistas importadas de Jamendo no se marcan ni se borran aquí."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select

from app.core.db import session_scope
from app.modules.catalog.import_jobs import create_job, get_job, run_import_job
from app.modules.catalog.models import Album, Artist, ImportJob, PublishedEvent, Song


@dataclass(frozen=True)
class DemoTrack:
    title: str
    genre: str
    audio_path: str
    duration: float
    status: str
    publish_at: datetime | None
    published_at: datetime | None


@dataclass(frozen=True)
class DemoComposer:
    user_id: UUID
    name: str
    bio: str
    tracks: list[DemoTrack]


@dataclass(frozen=True)
class ListenableSong:
    id: UUID
    artist_id: UUID
    duration: float
    source: str


async def insert_demo_catalog(composers: list[DemoComposer]) -> None:
    async with session_scope() as session:
        for composer in composers:
            artist = Artist(name=composer.name, owner_user_id=composer.user_id, bio=composer.bio, source="local", is_demo=True)
            session.add(artist)
            await session.flush()
            songs = [
                Song(
                    title=track.title,
                    artist_id=artist.id,
                    duration=track.duration,
                    genres=[track.genre],
                    source="local",
                    license="CC BY 4.0",
                    audio_path=track.audio_path,
                    status=track.status,
                    publish_at=track.publish_at,
                    published_at=track.published_at,
                    is_demo=True,
                )
                for track in composer.tracks
            ]
            session.add_all(songs)
            await session.flush()
            session.add_all(
                PublishedEvent(song_id=song.id, published_at=song.published_at)
                for song in songs
                if song.status == "published"
            )


async def clear_demo_catalog() -> None:
    demo_songs = select(Song.id).where(Song.is_demo.is_(True))
    async with session_scope() as session:
        await session.execute(delete(PublishedEvent).where(PublishedEvent.song_id.in_(demo_songs)))
        await session.execute(delete(Song).where(Song.is_demo.is_(True)))
        await session.execute(delete(Album).where(Album.is_demo.is_(True)))
        await session.execute(delete(Artist).where(Artist.is_demo.is_(True)))


async def listenable_songs(limit: int) -> list[ListenableSong]:
    """Todas las locales y hasta `limit` de Jamendo, en orden estable para que la semilla sea reproducible."""
    columns = (Song.id, Song.artist_id, Song.duration, Song.source)
    published = Song.status == "published"
    async with session_scope() as session:
        local = await session.execute(select(*columns).where(published, Song.source == "local").order_by(Song.id))
        jamendo = await session.execute(
            select(*columns).where(published, Song.source == "jamendo").order_by(Song.id).limit(limit)
        )
        return [ListenableSong(*row) for row in [*local.all(), *jamendo.all()]]


async def demo_import_done(genres: list[str], minimum: int) -> bool:
    wanted = {"seed": True, "genres": genres}
    query = (
        select(ImportJob.id)
        .where(ImportJob.status == "done", ImportJob.params.contains(wanted), ImportJob.imported >= minimum)
        .limit(1)
    )
    async with session_scope() as session:
        return await session.scalar(query) is not None


async def import_demo_catalog(genres: list[str], per_genre: int) -> tuple[str, int, str | None]:
    """Importa con el mismo trabajo que usa el Administrador. Devuelve estado, pistas y error."""
    job_id = await create_job(None, {"genres": genres, "limit_per_genre": per_genre, "seed": True})
    await run_import_job(job_id)
    job = await get_job(job_id)
    return job.status, job.imported, job.error
