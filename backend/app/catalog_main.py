from fastapi import Depends

from app.core.catalog_contract import BATCH_PATH, SongBatchRequest, SongBatchResponse
from app.core.internal import require_internal_token
from app.core.service_app import service_app
from app.modules.catalog.audit import deliver_pending
from app.modules.catalog.composer_routes import router as composer
from app.modules.catalog.public import get_songs, publish_due_tracks, refresh_metadata
from app.modules.catalog.routes import router as catalog

app = service_app("catalog", (catalog, composer), jobs=[
    ("publicar_programadas", 30, publish_due_tracks),
    ("refrescar_jamendo", 24 * 3600, refresh_metadata, 3600),
    ("entregar_auditoria", 5, deliver_pending),
])


@app.post(BATCH_PATH, dependencies=[Depends(require_internal_token)])
async def songs_batch(batch: SongBatchRequest) -> SongBatchResponse:
    songs = await get_songs(batch.ids)
    return SongBatchResponse(songs=list(songs.values()))
