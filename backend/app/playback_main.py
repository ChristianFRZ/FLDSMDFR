from uuid import UUID

from fastapi import Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, current_user
from app.core.db import get_session
from app.core.internal import require_internal_token
from app.modules.playback.queue import close_queue, consume
from app.modules.playback.schemas import PlaybackIn
from app.modules.playback.service import record
from app.core.service_app import service_app
from app.modules.analytics.public import refresh_aggregates
from app.modules.analytics.routes import router as analytics
from app.modules.playback.routes import router as playback

app = service_app("playback", (playback, analytics), jobs=[("agregados", 2, refresh_aggregates), ("reproducciones_pendientes", 1, consume)], shutdown=close_queue)


@app.post("/internal/playbacks/{delivery_id}", dependencies=[Depends(require_internal_token)], include_in_schema=False)
async def receive(delivery_id: UUID, data: PlaybackIn, response: Response, user: CurrentUser = Depends(current_user),
                  session: AsyncSession = Depends(get_session)):
    created = await record(session, user, data, delivery_id)
    response.status_code = 201 if created else 200
    return {"playback_id": data.playback_id, "counted": created}
