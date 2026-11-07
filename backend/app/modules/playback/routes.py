from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, current_user
from app.core.db import get_session
from app.core.pagination import PageParams, page_params
from app.modules.playback import service
from app.modules.playback.schemas import PlaybackIn, ProgressIn

router = APIRouter(prefix="/api/playbacks")


@router.post("")
async def record(
    data: PlaybackIn,
    response: Response,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    created = await service.record(session, user, data)
    response.status_code = 201 if created else 200
    return {"playback_id": data.playback_id, "counted": created}


@router.patch("/{playback_id}/progress")
async def progress(
    playback_id: UUID,
    data: ProgressIn,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    listened = await service.progress(session, user, playback_id, data.listened_seconds)
    return {"playback_id": playback_id, "listened_seconds": listened}


@router.get("/history")
async def history(
    params: PageParams = Depends(page_params),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.history(session, user, params)
