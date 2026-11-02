import uuid

from fastapi import APIRouter, Depends, Form, Header, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service
from app.modules.catalog.schemas import SongOut, SongPage, SongUpdate
from app.modules.catalog.streaming import file_response
from app.shared.deps import current_user, get_session, require_admin
from app.shared.images import image_response

router = APIRouter(prefix="/api", tags=["catalog"], dependencies=[Depends(current_user)])


@router.get("/songs", response_model=SongPage)
async def list_songs(
    q: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await service.list_songs(session, q, limit, offset)


@router.get("/songs/{song_id}", response_model=SongOut)
async def get_song(song_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_song(session, song_id)


@router.get("/songs/{song_id}/stream")
async def stream_song(
    song_id: uuid.UUID,
    range_header: str | None = Header(None, alias="Range"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    stream = await service.get_stream_file(session, song_id)
    return await file_response(stream.path, stream.mime_type, stream.size, range_header)


@router.post(
    "/songs", response_model=SongOut, status_code=201, dependencies=[Depends(require_admin)]
)
async def create_song(
    file: UploadFile,
    title: str = Form(..., min_length=1, max_length=200),
    artist: str = Form(..., min_length=1, max_length=200),
    album: str = Form(..., min_length=1, max_length=200),
    session: AsyncSession = Depends(get_session),
):
    return await service.create_song(session, title, artist, album, file)


@router.patch("/songs/{song_id}", response_model=SongOut, dependencies=[Depends(require_admin)])
async def update_song(
    song_id: uuid.UUID, data: SongUpdate, session: AsyncSession = Depends(get_session)
):
    return await service.update_song(session, song_id, data)


@router.delete("/songs/{song_id}", status_code=204, dependencies=[Depends(require_admin)])
async def deactivate_song(
    song_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    await service.deactivate_song(session, song_id)
    return Response(status_code=204)


@router.put("/songs/{song_id}/cover", response_model=SongOut, dependencies=[Depends(require_admin)])
async def set_cover(
    song_id: uuid.UUID, file: UploadFile, session: AsyncSession = Depends(get_session)
):
    return await service.set_cover(session, song_id, file)


@router.get("/songs/{song_id}/cover")
async def get_cover(
    song_id: uuid.UUID,
    if_none_match: str | None = Header(None, alias="If-None-Match"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    return image_response(await service.get_cover_file(session, song_id), if_none_match)
