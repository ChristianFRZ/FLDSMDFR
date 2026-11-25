"""Contrato de la cola de reproducciones: catálogo la llena y playback-metrics la consume."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError

STREAM = "playbacks"
GROUP = "playbacks"
MAXLEN = 100_000
MAX_SECONDS = 86400


@dataclass(frozen=True)
class QueuedEvent:
    type: Literal["record", "progress"]
    user_id: UUID
    playback_id: UUID
    listened_seconds: int
    song_id: UUID | None
    received_at: str


def to_fields(event: QueuedEvent) -> dict[str, str]:
    fields = {
        "type": event.type,
        "user_id": str(event.user_id),
        "playback_id": str(event.playback_id),
        "listened_seconds": str(event.listened_seconds),
        "received_at": event.received_at,
    }
    if event.song_id is not None:
        fields["song_id"] = str(event.song_id)
    return fields


def from_fields(fields: dict[str, str]) -> QueuedEvent:
    """Lanza `ValueError` si el mensaje está incompleto o tiene valores que no se pueden leer."""
    try:
        kind = fields["type"]
        if kind not in ("record", "progress"):
            raise ValueError(f"tipo desconocido: {kind}")
        seconds = int(fields["listened_seconds"])
        if not 0 <= seconds <= MAX_SECONDS:
            raise ValueError("segundos fuera de rango")
        song = fields.get("song_id")
        if kind == "record" and song is None:
            raise ValueError("falta song_id")
        received = fields["received_at"]
        datetime.fromisoformat(received)
        return QueuedEvent(
            type=kind,
            user_id=UUID(fields["user_id"]),
            playback_id=UUID(fields["playback_id"]),
            listened_seconds=seconds,
            song_id=UUID(song) if song else None,
            received_at=received,
        )
    except KeyError as exc:
        raise ValueError(f"falta el campo {exc.args[0]}") from exc


async def enqueue(redis: Redis, event: QueuedEvent) -> str:
    return await redis.xadd(STREAM, to_fields(event), maxlen=MAXLEN, approximate=True)


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise
