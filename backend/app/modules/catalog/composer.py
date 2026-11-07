"""Pistas, álbumes y perfil de Compositores."""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.catalog import uploads
from app.modules.catalog.models import Album, Artist, Song
from app.modules.catalog.publishing import record_published
from app.modules.catalog.schemas import ProfileIn, TrackPatch
from app.modules.catalog.service import media_url, to_artist_summary, to_summary
from app.modules.users.public import get_display_names


def _forbidden() -> AppError:
    return AppError(403, "forbidden", "Esta pista no es tuya")


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _check_future(moment: datetime) -> datetime:
    moment = as_utc(moment)
    if moment <= datetime.now(UTC):
        raise AppError(422, "publish_at_past", "La fecha de publicación debe estar en el futuro")
    return moment


async def ensure_artist(session: AsyncSession, user_id: UUID) -> Artist:
    query = select(Artist).where(Artist.owner_user_id == user_id).with_for_update()
    artist = (await session.execute(query)).scalar_one_or_none()
    if artist is None:
        names = await get_display_names([user_id])
        artist = Artist(name=names.get(user_id, "Sin nombre"), source="local", owner_user_id=user_id)
        session.add(artist)
        await session.flush()
    return artist


async def _owned_album(session: AsyncSession, album_id: UUID | None, artist: Artist) -> UUID | None:
    if album_id is None:
        return None
    album = await session.get(Album, album_id)
    if album is None or album.artist_id != artist.id:
        raise AppError(403, "forbidden", "Ese álbum no es tuyo")
    return album.id


async def create_track(
    session: AsyncSession,
    user: CurrentUser,
    audio: UploadFile,
    cover: UploadFile | None,
    title: str,
    genre: str,
    license_name: str,
    publish_at: datetime | None,
    album_id: UUID | None,
) -> dict:
    moment = _check_future(publish_at) if publish_at else None
    artist = await ensure_artist(session, user.id)
    album = await _owned_album(session, album_id, artist)
    count = await session.scalar(select(func.count()).select_from(Song).where(Song.artist_id == artist.id))
    if (count or 0) >= get_settings().COMPOSER_MAX_TRACKS:
        raise AppError(409, "quota_exceeded", "Alcanzaste el máximo de pistas de tu cuenta")
    audio_path, duration = await uploads.store_audio(audio)
    cover_path = None
    try:
        if cover is not None:
            cover_path = await uploads.store_cover(cover)
        song = Song(
            title=title,
            artist_id=artist.id,
            album_id=album,
            duration=duration,
            genres=[genre],
            tags=[],
            source="local",
            license=license_name,
            audio_path=audio_path,
            cover_path=cover_path,
            status="scheduled" if moment else "draft",
            publish_at=moment,
        )
        session.add(song)
        await session.commit()
    except BaseException:
        uploads.delete_media(audio_path, cover_path)
        raise
    return await track_out(session, song.id)


async def _load_owned(session: AsyncSession, user: CurrentUser, song_id: UUID) -> Song:
    song = await session.get(Song, song_id)
    if song is None:
        raise AppError(404, "song_not_found", "Canción no encontrada")
    if song.artist.owner_user_id != user.id:
        raise _forbidden()
    return song


async def track_out(session: AsyncSession, song_id: UUID) -> dict:
    song = await session.get(Song, song_id, populate_existing=True)
    return {
        **to_summary(song).__dict__,
        "album_id": song.album_id,
        "publish_at": song.publish_at,
        "published_at": song.published_at,
        "hidden_reason": song.hidden_reason,
        "hidden_by_admin": song.hidden_by_admin,
    }


async def list_tracks(session: AsyncSession, user: CurrentUser) -> list[dict]:
    query = (
        select(Song.id)
        .join(Artist, Song.artist_id == Artist.id)
        .where(Artist.owner_user_id == user.id)
        .order_by(Song.created_at.desc())
    )
    ids = list((await session.execute(query)).scalars())
    return [await track_out(session, song_id) for song_id in ids]


async def update_track(session: AsyncSession, user: CurrentUser, song_id: UUID, data: TrackPatch) -> dict:
    song = await _load_owned(session, user, song_id)
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes:
        song.title = changes["title"]
    if "genre" in changes:
        song.genres = [changes["genre"]]
    if "license" in changes:
        song.license = changes["license"]
    if "album_id" in changes:
        song.album_id = await _owned_album(session, changes["album_id"], song.artist)
    if "publish_at" in changes:
        if song.status not in ("draft", "scheduled"):
            raise AppError(409, "not_schedulable", "Solo se programan pistas sin publicar")
        moment = changes["publish_at"]
        song.publish_at = _check_future(moment) if moment else None
        song.status = "scheduled" if moment else "draft"
    await session.commit()
    return await track_out(session, song.id)


async def hide_track(session: AsyncSession, user: CurrentUser, song_id: UUID) -> dict:
    song = await _load_owned(session, user, song_id)
    song.status = "hidden"
    await session.commit()
    return await track_out(session, song.id)


async def publish_track(session: AsyncSession, user: CurrentUser, song_id: UUID) -> dict:
    song = await _load_owned(session, user, song_id)
    if song.hidden_by_admin:
        raise AppError(403, "hidden_by_admin", "Un administrador ocultó esta pista")
    song.status = "published"
    song.published_at = song.published_at or datetime.now(UTC)
    song.publish_at = None
    await record_published(session, song.id)
    await session.commit()
    return await track_out(session, song.id)


async def delete_track(session: AsyncSession, user: CurrentUser, song_id: UUID) -> None:
    song = await _load_owned(session, user, song_id)
    paths = (song.audio_path, song.cover_path)
    await session.delete(song)
    await session.commit()
    uploads.delete_media(*paths)


async def get_profile(session: AsyncSession, user: CurrentUser):
    artist = await ensure_artist(session, user.id)
    await session.commit()
    return to_artist_summary(artist)


async def update_profile(session: AsyncSession, user: CurrentUser, data: ProfileIn):
    artist = await ensure_artist(session, user.id)
    artist.name = data.name
    artist.bio = data.bio
    artist.links = data.links
    await session.commit()
    return to_artist_summary(artist)


async def update_photo(session: AsyncSession, user: CurrentUser, photo: UploadFile):
    artist = await ensure_artist(session, user.id)
    path = await uploads.store_cover(photo)
    previous, artist.photo_path = artist.photo_path, path
    await session.commit()
    uploads.delete_media(previous)
    return to_artist_summary(artist)


def _album_out(album: Album) -> dict:
    return {"id": album.id, "title": album.title, "kind": album.kind, "cover_url": media_url(album.cover_path)}


async def create_album(
    session: AsyncSession, user: CurrentUser, title: str, kind: str, cover: UploadFile | None
) -> dict:
    artist = await ensure_artist(session, user.id)
    path = await uploads.store_cover(cover) if cover is not None else None
    album = Album(title=title, kind=kind, artist_id=artist.id, cover_path=path)
    session.add(album)
    await session.commit()
    return _album_out(album)


async def list_albums(session: AsyncSession, user: CurrentUser) -> list[dict]:
    query = select(Album).join(Artist, Album.artist_id == Artist.id).where(Artist.owner_user_id == user.id)
    return [_album_out(a) for a in (await session.execute(query.order_by(Album.title))).scalars()]
