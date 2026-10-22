from fastapi import APIRouter, Header, HTTPException, Query, status

from core.module_catalog.models import SongCreate, SongResponse
from core.module_catalog.service import CatalogService
from core.module_catalog.streaming import handle_range_streaming

router = APIRouter(prefix="/songs", tags=["Catalog & Streaming"])


@router.get("", response_model=list[SongResponse])
def list_songs(q: str | None = Query(None, description="Término de búsqueda opcional")):
    return CatalogService.list_songs(query=q)


@router.post("", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
def create_song(payload: SongCreate):
    return CatalogService.create_song(payload)


@router.get("/{song_id}", response_model=SongResponse)
def get_song(song_id: int):
    song = CatalogService.get_song_by_id(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canción con id {song_id} no encontrada.",
        )
    return song


@router.get("/{song_id}/stream")
def stream_song(song_id: int, range: str | None = Header(None)):
    """Entrega el flujo binario de audio admitiendo peticiones con cabeceras 'Range: bytes=...'

    (HTTP 206 Partial Content) para permitir pausa, reanudación y buffering instantáneo.
    """
    song = CatalogService.get_song_by_id(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canción con id {song_id} no encontrada.",
        )
    return handle_range_streaming(
        file_path_str=song.file_path,
        range_header=range,
        mime_type=song.mime_type,
    )
