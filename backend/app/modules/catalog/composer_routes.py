from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, require_role
from app.core.db import get_session
from app.core.errors import AppError
from app.modules.catalog import composer, uploads
from app.modules.catalog.schemas import ProfileIn, TrackPatch

router = APIRouter(prefix="/api")
can_compose = require_role("composer", "admin")


@router.post("/composer/tracks", status_code=201)
async def create_track(
    audio: UploadFile = File(),
    cover: UploadFile | None = File(default=None),
    title: str = Form(min_length=1, max_length=300),
    genre: str = Form(min_length=1, max_length=60),
    license: str = Form(min_length=1, max_length=120),
    publish_at: datetime | None = Form(default=None),
    album_id: UUID | None = Form(default=None),
    user: CurrentUser = Depends(can_compose),
    session: AsyncSession = Depends(get_session),
):
    return await composer.create_track(session, user, audio, cover, title, genre, license, publish_at, album_id)


@router.get("/composer/tracks")
async def tracks(user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)):
    return await composer.list_tracks(session, user)


@router.patch("/composer/tracks/{song_id}")
async def edit_track(
    song_id: UUID,
    data: TrackPatch,
    user: CurrentUser = Depends(can_compose),
    session: AsyncSession = Depends(get_session),
):
    return await composer.update_track(session, user, song_id, data)


@router.delete("/composer/tracks/{song_id}", status_code=204)
async def delete_track(
    song_id: UUID, user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)
):
    await composer.delete_track(session, user, song_id)
    return Response(status_code=204)


@router.post("/composer/tracks/{song_id}/hide")
async def hide_track(
    song_id: UUID, user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)
):
    return await composer.hide_track(session, user, song_id)


@router.post("/composer/tracks/{song_id}/publish")
async def publish_track(
    song_id: UUID, user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)
):
    return await composer.publish_track(session, user, song_id)


@router.get("/composer/profile")
async def profile(user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)):
    return await composer.get_profile(session, user)


@router.put("/composer/profile")
async def edit_profile(
    data: ProfileIn, user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)
):
    return await composer.update_profile(session, user, data)


@router.post("/composer/profile/photo")
async def edit_photo(
    photo: UploadFile = File(),
    user: CurrentUser = Depends(can_compose),
    session: AsyncSession = Depends(get_session),
):
    return await composer.update_photo(session, user, photo)


@router.post("/composer/albums", status_code=201)
async def create_album(
    title: str = Form(min_length=1, max_length=200),
    kind: Literal["album", "ep"] = Form(default="album"),
    cover: UploadFile | None = File(default=None),
    user: CurrentUser = Depends(can_compose),
    session: AsyncSession = Depends(get_session),
):
    return await composer.create_album(session, user, title, kind, cover)


@router.get("/composer/albums")
async def albums(user: CurrentUser = Depends(can_compose), session: AsyncSession = Depends(get_session)):
    return await composer.list_albums(session, user)


@router.get("/media/{path:path}")
async def media(path: str):
    file = uploads.resolve_cover(path)
    if file is None:
        raise AppError(404, "not_found", "Archivo no encontrado")
    return FileResponse(file)
