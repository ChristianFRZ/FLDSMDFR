"""API interna del catálogo para otros servicios (red de Compose, sin sesión).

El proxy no expone /internal: solo users-playlists y playback-metrics la usan. Cada ruta
delega en `service` y conserva el contrato que antes era un import dentro del monolito.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service
from app.modules.catalog.schemas import SongOut
from app.shared.deps import get_session
from app.shared.errors import NotFound

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


class IdsIn(BaseModel):
    ids: list[uuid.UUID]


class ArtistsIn(BaseModel):
    artists: list[str]


class FollowIn(BaseModel):
    artist: str
    since: datetime


class ReleasesIn(BaseModel):
    follows: list[FollowIn]
    not_before: datetime


class CountOut(BaseModel):
    count: int


@router.get("/songs/count", response_model=CountOut)
async def count_songs(session: AsyncSession = Depends(get_session)) -> CountOut:
    return CountOut(count=await service.count_songs(session))


@router.get("/songs/lookup", response_model=SongOut)
async def lookup(
    title: str = Query(min_length=1),
    artist: str = Query(min_length=1),
    session: AsyncSession = Depends(get_session),
) -> SongOut:
    song = await service.find_song_by_title_artist(session, title, artist)
    if song is None:
        raise NotFound("La canción no existe.", code="song_not_found")
    return song


@router.get("/songs/{song_id}", response_model=SongOut)
async def get_song(song_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> SongOut:
    return await service.get_song(session, song_id)


@router.post("/songs/batch", response_model=list[SongOut])
async def batch(data: IdsIn, session: AsyncSession = Depends(get_session)) -> list[SongOut]:
    """Incluye las inactivas: quien llama usa `is_active` para marcarlas como no disponibles."""
    return list((await service.get_songs_by_ids(session, data.ids)).values())


@router.post("/artists/counts", response_model=dict[str, int])
async def artist_counts(
    data: ArtistsIn, session: AsyncSession = Depends(get_session)
) -> dict[str, int]:
    return await service.count_active_by_artists(session, data.artists)


@router.post("/artists/latest", response_model=dict[str, SongOut])
async def artist_latest(
    data: ArtistsIn, session: AsyncSession = Depends(get_session)
) -> dict[str, SongOut]:
    return await service.latest_song_by_artists(session, data.artists)


@router.post("/artists/releases", response_model=list[SongOut])
async def releases(data: ReleasesIn, session: AsyncSession = Depends(get_session)) -> list[SongOut]:
    follows = [(f.artist, f.since) for f in data.follows]
    return await service.songs_by_artists_since(session, follows, data.not_before)
