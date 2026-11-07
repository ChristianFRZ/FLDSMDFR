from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.pagination import PageParams
from app.modules.catalog.models import Artist, Song
from app.modules.catalog.schemas import ArtistSummary, SongSummary


def media_url(path: str | None) -> str | None:
    return f"/api/media/{path}" if path else None


def to_summary(song: Song) -> SongSummary:
    cover = media_url(song.cover_path) or song.cover_url
    if cover is None and song.album is not None:
        cover = media_url(song.album.cover_path) or song.album.cover_url
    return SongSummary(
        id=song.id,
        title=song.title,
        artist_id=song.artist_id,
        artist=song.artist.name,
        album=song.album.title if song.album else None,
        duration=song.duration,
        cover_url=cover,
        source=song.source,
        license=song.license,
        license_url=song.license_url,
        jamendo_url=song.jamendo_url,
        genres=tuple(song.genres),
        status=song.status,
        available=song.status == "published",
    )


def to_artist_summary(artist: Artist) -> ArtistSummary:
    return ArtistSummary(
        id=artist.id,
        name=artist.name,
        source=artist.source,
        bio=artist.bio,
        photo_url=media_url(artist.photo_path),
        links=artist.links,
    )


async def search_songs(
    session: AsyncSession,
    params: PageParams,
    q: str | None = None,
    genre: str | None = None,
    artist: str | None = None,
    tag: str | None = None,
    source: str | None = None,
) -> tuple[list[SongSummary], int]:
    filters = [Song.status == "published"]
    if q:
        like = f"%{q}%"
        filters.append(Song.title.ilike(like) | Artist.name.ilike(like))
    if genre:
        filters.append(Song.genres.contains([genre]))
    if tag:
        filters.append(Song.tags.contains([tag]))
    if artist:
        filters.append(Artist.name.ilike(f"%{artist}%"))
    if source:
        filters.append(Song.source == source)
    total = await session.scalar(select(func.count(Song.id)).join(Artist, Song.artist_id == Artist.id).where(*filters))
    query = (
        select(Song)
        .join(Artist, Song.artist_id == Artist.id)
        .where(*filters)
        .order_by(Song.title, Song.id)
        .offset(params.offset)
        .limit(params.size)
    )
    return [to_summary(s) for s in (await session.execute(query)).unique().scalars()], total or 0


async def get_published_song(session: AsyncSession, song_id: UUID) -> Song:
    song = await session.get(Song, song_id)
    if song is None or song.status != "published":
        raise AppError(404, "song_not_found", "Canción no encontrada")
    return song


async def artist_page(session: AsyncSession, artist_id: UUID) -> dict:
    artist = await session.get(Artist, artist_id)
    if artist is None:
        raise AppError(404, "artist_not_found", "Artista no encontrado")
    query = select(Song).where(Song.artist_id == artist_id, Song.status == "published").order_by(Song.title)
    songs = [to_summary(s) for s in (await session.execute(query)).unique().scalars()]
    return {**to_artist_summary(artist).__dict__, "songs": songs}


async def list_genres(session: AsyncSession) -> list[str]:
    query = select(func.unnest(Song.genres)).where(Song.status == "published").distinct()
    return sorted((await session.execute(query)).scalars())
