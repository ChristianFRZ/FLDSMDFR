from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, current_user
from app.core.db import get_session
from app.core.pagination import PageParams, page_params
from app.modules.social import service

router = APIRouter(prefix="/api")


@router.put("/favorites/{song_id}", status_code=204)
async def add_favorite(
    song_id: UUID, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await service.add_favorite(session, user, song_id)
    return Response(status_code=204)


@router.delete("/favorites/{song_id}", status_code=204)
async def remove_favorite(
    song_id: UUID, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await service.remove_favorite(session, user, song_id)
    return Response(status_code=204)


@router.get("/favorites")
async def favorites(
    params: PageParams = Depends(page_params),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.list_favorites(session, user, params)


@router.get("/favorites/ids")
async def favorite_ids(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.favorite_ids(session, user)


@router.get("/follows/ids")
async def followed_ids(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return list(await service.followed_artists(session, user))


@router.put("/follows/{artist_id}", status_code=204)
async def follow(
    artist_id: UUID, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await service.follow(session, user, artist_id)
    return Response(status_code=204)


@router.delete("/follows/{artist_id}", status_code=204)
async def unfollow(
    artist_id: UUID, user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await service.unfollow(session, user, artist_id)
    return Response(status_code=204)


@router.get("/follows")
async def follows(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.list_follows(session, user)


@router.get("/notices")
async def notices(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.notices(session, user)


@router.post("/notices/seen", status_code=204)
async def mark_seen(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    await service.mark_seen(session, user)
    return Response(status_code=204)


@router.get("/releases")
async def releases(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.releases(session, user)
