from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playback import service
from app.modules.playback.schemas import (
    HistoryPage,
    MetricsSummary,
    PlaybackIn,
    PlaybackOut,
    TopArtistOut,
    TopSongOut,
)
from app.shared.deps import CurrentUser, current_user, get_session, require_admin

router = APIRouter(prefix="/api", tags=["playback"])


@router.post("/playbacks", status_code=201, response_model=PlaybackOut)
async def record_playback(
    data: PlaybackIn,
    response: Response,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    counted = await service.record_playback(session, user.user_id, data)
    if not counted:
        response.status_code = 200
    return PlaybackOut(playback_id=data.playback_id, counted=counted)


@router.get("/metrics/top", response_model=list[TopSongOut])
async def top(
    limit: int = Query(10, ge=1, le=50),
    _: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.top_songs(session, limit)


@router.get("/metrics/summary", response_model=MetricsSummary)
async def summary(
    _: CurrentUser = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    return await service.summary(session)


@router.get("/metrics/top-artists", response_model=list[TopArtistOut])
async def top_artists(
    limit: int = Query(5, ge=1, le=20),
    _: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.top_artists(session, limit)


@router.get("/me/history", response_model=HistoryPage)
async def history(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.recent_for_user(session, user.user_id, limit, offset)
