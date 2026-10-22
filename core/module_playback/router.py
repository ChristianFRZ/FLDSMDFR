from fastapi import APIRouter, HTTPException, Query, status

from core.module_playback.models import (
    PlaybackEventCreate,
    PlaybackEventResponse,
    TopSongMetric,
)
from core.module_playback.service import PlaybackService

playbacks_router = APIRouter(prefix="/playbacks", tags=["Playbacks"])
metrics_router = APIRouter(prefix="/metrics", tags=["Metrics"])


@playbacks_router.post(
    "", response_model=PlaybackEventResponse, status_code=status.HTTP_201_CREATED
)
def record_playback(payload: PlaybackEventCreate):
    try:
        return PlaybackService.record_playback(payload)
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err))


@metrics_router.get("/top", response_model=list[TopSongMetric])
def get_top_metrics(limit: int = Query(10, ge=1, le=100)):
    return PlaybackService.get_top_metrics(limit=limit)


@metrics_router.get("/songs/{song_id}", response_model=TopSongMetric)
def get_song_metric(song_id: int):
    metric = PlaybackService.get_song_metric(song_id)
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Métrica para la canción con id {song_id} no encontrada.",
        )
    return metric
