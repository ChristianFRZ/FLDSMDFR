import uuid

from fastapi import APIRouter, Depends, Header, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playlists import service
from app.modules.playlists.schemas import (
    AddSongIn,
    PlaylistDetail,
    PlaylistIn,
    PlaylistSummary,
    ReorderIn,
)
from app.shared.deps import CurrentUser, current_user, get_session
from app.shared.images import image_response

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistSummary])
async def list_playlists(
    user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return await service.list_playlists(session, user.user_id)


@router.post("", status_code=201, response_model=PlaylistSummary)
async def create_playlist(
    data: PlaylistIn,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.create_playlist(session, user.user_id, data)


@router.get("/{playlist_id}", response_model=PlaylistDetail)
async def get_playlist(
    playlist_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.get_playlist(session, user.user_id, playlist_id)


@router.patch("/{playlist_id}", response_model=PlaylistSummary)
async def rename_playlist(
    playlist_id: uuid.UUID,
    data: PlaylistIn,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.rename_playlist(session, user.user_id, playlist_id, data)


@router.delete("/{playlist_id}", status_code=204)
async def delete_playlist(
    playlist_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await service.delete_playlist(session, user.user_id, playlist_id)
    return Response(status_code=204)


@router.post("/{playlist_id}/songs", status_code=201, response_model=PlaylistDetail)
async def add_song(
    playlist_id: uuid.UUID,
    data: AddSongIn,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.add_song(session, user.user_id, playlist_id, data.song_id)


@router.delete("/{playlist_id}/songs/{song_id}", response_model=PlaylistDetail)
async def remove_song(
    playlist_id: uuid.UUID,
    song_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.remove_song(session, user.user_id, playlist_id, song_id)


@router.put("/{playlist_id}/order", response_model=PlaylistDetail)
async def reorder(
    playlist_id: uuid.UUID,
    data: ReorderIn,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.reorder(session, user.user_id, playlist_id, data)


@router.put("/{playlist_id}/cover", response_model=PlaylistSummary)
async def set_cover(
    playlist_id: uuid.UUID,
    file: UploadFile,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.set_cover(session, user.user_id, playlist_id, file)


@router.get("/{playlist_id}/cover")
async def get_cover(
    playlist_id: uuid.UUID,
    if_none_match: str | None = Header(None, alias="If-None-Match"),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    path = await service.get_cover_file(session, user.user_id, playlist_id)
    return image_response(path, if_none_match)


@router.delete("/{playlist_id}/members/{member_id}", status_code=204)
async def remove_member(
    playlist_id: uuid.UUID,
    member_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await service.remove_member(session, user.user_id, playlist_id, member_id)
    return Response(status_code=204)
