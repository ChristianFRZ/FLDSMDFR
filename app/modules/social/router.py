import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.social import service
from app.modules.social.schemas import FavoritesOut
from app.shared.deps import CurrentUser, current_user, get_session

router = APIRouter(prefix="/api/me", tags=["social"])


@router.get("/favorites", response_model=FavoritesOut)
async def list_favorites(
    user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return await service.list_favorites(session, user.user_id)


@router.get("/favorites/ids", response_model=list[uuid.UUID])
async def favorite_ids(
    user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return await service.favorite_ids(session, user.user_id)


@router.put("/favorites/{song_id}", status_code=204)
async def like(
    song_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await service.like(session, user.user_id, song_id)
    return Response(status_code=204)


@router.delete("/favorites/{song_id}", status_code=204)
async def unlike(
    song_id: uuid.UUID,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await service.unlike(session, user.user_id, song_id)
    return Response(status_code=204)
