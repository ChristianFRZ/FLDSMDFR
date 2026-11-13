"""Rutas `/internal/*`: salud y herramientas de la semilla de demo.

nginx no las publica y no llevan autenticación: solo las llaman otros servicios dentro de la red de Docker.
"""
import time
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from meloxo_common.db import session_scope

from playback_metrics.modules.analytics.public import catch_up_aggregates, rebuild_aggregates
from playback_metrics.modules.playback.public import DemoPlay, clear_demo_playbacks, insert_demo_playbacks

router = APIRouter(prefix="/internal")
_started = time.monotonic()


@router.get("/health")
async def health() -> dict:
    """Siempre 200: si la base no responde, `status` es `down` y `database_ms` es 0."""
    start = time.perf_counter()
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        status, database_ms = "up", (time.perf_counter() - start) * 1000
    except Exception:
        status, database_ms = "down", 0.0
    return {
        "name": "playback-metrics",
        "status": status,
        "database_ms": float(database_ms),
        "uptime_seconds": int(time.monotonic() - _started),
    }


class DemoPlayIn(BaseModel):
    user_id: UUID
    song_id: UUID
    listened_seconds: int
    started_at: datetime


class DemoPlaybacksIn(BaseModel):
    plays: list[DemoPlayIn]
    duplicates: int = Field(0, ge=0)


@router.post("/demo/playbacks", status_code=204)
async def insert_demo(body: DemoPlaybacksIn) -> None:
    await insert_demo_playbacks([DemoPlay(**p.model_dump()) for p in body.plays], body.duplicates)


@router.post("/demo/playbacks/clear", status_code=204)
async def clear_demo() -> None:
    await clear_demo_playbacks()


@router.post("/demo/aggregates/rebuild", status_code=204)
async def rebuild() -> None:
    await rebuild_aggregates()


@router.post("/demo/aggregates/catch-up", status_code=204)
async def catch_up() -> None:
    await catch_up_aggregates()
