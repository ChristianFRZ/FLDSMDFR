"""Entrada de las reproducciones: valida, encola en Redis y responde 202. playback-metrics las aplica después."""
import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from meloxo_common import playback_queue as queue
from meloxo_common import redis_client
from meloxo_common.auth import CurrentUser
from meloxo_common.errors import AppError
from meloxo_common.internal import UpstreamError

from catalog_streaming.auth import auth
from catalog_streaming.modules.catalog import public

router = APIRouter(prefix="/api/playbacks")
ENQUEUE_TIMEOUT_SECONDS = 1.0


class PlaybackIn(BaseModel):
    playback_id: UUID
    song_id: UUID
    listened_seconds: int = Field(ge=0, le=queue.MAX_SECONDS)


class ProgressIn(BaseModel):
    listened_seconds: int = Field(ge=0, le=queue.MAX_SECONDS)


async def _enqueue(event: queue.QueuedEvent) -> None:
    redis = redis_client.get_redis()
    if redis is None:
        raise UpstreamError("La cola de reproducciones no está disponible", detail="redis_disabled")
    try:
        await asyncio.wait_for(queue.enqueue(redis, event), ENQUEUE_TIMEOUT_SECONDS)
    except Exception as exc:
        raise UpstreamError("La cola de reproducciones no responde", detail=type(exc).__name__) from exc


def _now() -> str:
    return datetime.now(UTC).isoformat()


@router.post("", status_code=202)
async def record(data: PlaybackIn, user: CurrentUser = Depends(auth.current_user)) -> dict[str, UUID]:
    if data.song_id not in await public.get_songs([data.song_id]):
        raise AppError(404, "song_not_found", "Canción no encontrada")
    await _enqueue(
        queue.QueuedEvent("record", user.id, data.playback_id, data.listened_seconds, data.song_id, _now())
    )
    return {"playback_id": data.playback_id}


@router.patch("/{playback_id}/progress", status_code=202)
async def progress(
    playback_id: UUID, data: ProgressIn, user: CurrentUser = Depends(auth.current_user)
) -> dict[str, UUID]:
    await _enqueue(queue.QueuedEvent("progress", user.id, playback_id, data.listened_seconds, None, _now()))
    return {"playback_id": playback_id}
