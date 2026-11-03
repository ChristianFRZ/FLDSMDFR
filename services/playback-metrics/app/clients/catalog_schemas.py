"""Contrato de una canción tal como la expone catalog-streaming en /internal.

Es una copia del `SongOut` del catálogo: la fuente de verdad vive en ese servicio.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SongOut(BaseModel):
    id: uuid.UUID
    title: str
    artist: str
    album: str
    duration_seconds: int
    is_active: bool
    has_cover: bool = False
    created_at: datetime | None = None
    size_bytes: int = 0
    mime_type: str = ""
