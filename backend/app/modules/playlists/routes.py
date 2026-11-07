from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, current_user
from app.core.db import get_session
from app.modules.playlists import service
from app.modules.playlists.schemas import AddSongIn, PlaylistIn, PlaylistOut, PlaylistPatch

router = APIRouter(prefix="/api/playlists")


@router.post("", response_model=PlaylistOut, status_code=201)
async def create(
    data: PlaylistIn, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return await service.create(session, user, data)


@router.get("", response_model=list[PlaylistOut])
async def mine(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.list_mine(session, user)


@router.get("/{playlist_id}")
async def detail(
    playlist_id: UUID, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return await service.detail(session, user, playlist_id)


@router.patch("/{playlist_id}", response_model=PlaylistOut)
async def update(
    playlist_id: UUID,
    data: PlaylistPatch,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.update(session, user, playlist_id, data)


@router.delete("/{playlist_id}", status_code=204)
async def delete(
    playlist_id: UUID, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await service.delete(session, user, playlist_id)
    return Response(status_code=204)


@router.post("/{playlist_id}/songs")
async def add_song(
    playlist_id: UUID,
    data: AddSongIn,
    response: Response,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    added = await service.add_song(session, user, playlist_id, data.song_id)
    response.status_code = 201 if added else 200
    return {"added": added}


@router.delete("/{playlist_id}/songs/{song_id}", status_code=204)
async def remove_song(
    playlist_id: UUID,
    song_id: UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await service.remove_song(session, user, playlist_id, song_id)
    return Response(status_code=204)
