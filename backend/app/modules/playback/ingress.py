"""Entrada del gateway para registrar escuchas incluso durante una caída de Métricas."""
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Request, Response

from app.core.auth import CurrentUser, current_user
from app.core.breaker import CircuitBreaker
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.internal import HOSTS, internal_client
from app.modules.playback.queue import enqueue
from app.modules.playback.schemas import PlaybackIn

router = APIRouter()
breaker = CircuitBreaker()


def unavailable():
    return AppError(503, "playback_unavailable", "Métricas no responde")


@router.post("/api/playbacks")
async def submit(data: PlaybackIn, request: Request, response: Response, user: CurrentUser = Depends(current_user)):
    delivery_id = uuid4()
    headers = {"Authorization": request.headers["authorization"],
               "X-Catalog-Token": get_settings().CATALOG_INTERNAL_TOKEN.get_secret_value()}
    try:
        with breaker.request(unavailable):
            try:
                async with internal_client() as client:
                    result = await client.post(f"{HOSTS['playback']}/internal/playbacks/{delivery_id}",
                                               headers=headers, json=data.model_dump(mode="json"), timeout=1.5)
            except httpx.RequestError as exc:
                raise unavailable() from exc
            if result.status_code >= 500:
                raise unavailable()
            return Response(result.content, status_code=result.status_code, media_type="application/json")
    except AppError:
        await enqueue(user, data, delivery_id)
        response.status_code = 202
        return {"playback_id": data.playback_id, "queued": True}
