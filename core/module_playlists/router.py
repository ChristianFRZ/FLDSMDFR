from fastapi import APIRouter, HTTPException, status

from core.module_playlists.models import (
    PlaylistAddSong,
    PlaylistCreate,
    PlaylistDetailResponse,
    PlaylistResponse,
)
from core.module_playlists.service import PlaylistService

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(payload: PlaylistCreate):
    try:
        return PlaylistService.create_playlist(payload)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/{playlist_id}/songs", status_code=status.HTTP_200_OK)
def add_song_to_playlist(playlist_id: int, payload: PlaylistAddSong):
    try:
        PlaylistService.add_song_to_playlist(playlist_id, payload.song_id)
        return {"message": "Canción agregada exitosamente a la playlist."}
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
def get_playlist(playlist_id: int):
    detail = PlaylistService.get_playlist_details(playlist_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playlist con id {playlist_id} no encontrada.",
        )
    return detail


@router.get("", response_model=list[PlaylistResponse])
def list_playlists(user_id: int | None = None):
    if user_id:
        return PlaylistService.list_playlists_by_user(user_id)
    return PlaylistService.list_all_playlists()
