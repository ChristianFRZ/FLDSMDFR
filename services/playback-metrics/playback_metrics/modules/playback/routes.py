from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meloxo_common.auth import CurrentUser
from playback_metrics.auth import current_user
from meloxo_common.db import get_session
from meloxo_common.pagination import PageParams, page_params
from playback_metrics.modules.playback import service

router = APIRouter(prefix="/api/playbacks")


@router.get("/history")
async def history(
    params: PageParams = Depends(page_params),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.history(session, user, params)
