import uuid

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog import service
from app.modules.catalog.schemas import SongOut, SongPage
from app.modules.catalog.streaming import file_response
from app.shared.deps import current_user, get_session

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
