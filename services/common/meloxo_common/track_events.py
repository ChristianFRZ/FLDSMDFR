"""Contrato del evento `track_published`: catálogo lo publica en un stream y `users-playlists` lo consume."""
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import ResponseError

STREAM = "track_published"
DLQ_STREAM = "track_published:dlq"
GROUP = "users-playlists"
MAXLEN = 100_000
MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class TrackPublished:
    song_id: UUID
    artist_id: UUID
    published_at: str  # ISO 8601
    song: dict  # el SongSummary de la pista, como JSON


def to_fields(event: TrackPublished) -> dict[str, str]:
    return {
        "song_id": str(event.song_id),
        "artist_id": str(event.artist_id),
        "published_at": event.published_at,
        "song": json.dumps(event.song, separators=(",", ":")),
    }


def from_fields(fields: dict[str, str]) -> TrackPublished:
    """Lanza `ValueError` con el motivo si el mensaje está incompleto o no se puede leer."""
    try:
        song_id = UUID(fields["song_id"])
        artist_id = UUID(fields["artist_id"])
        published_at = fields["published_at"]
        datetime.fromisoformat(published_at)
        song = json.loads(fields["song"])
    except KeyError as exc:
        raise ValueError(f"falta el campo {exc.args[0]}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"song no es JSON: {exc}") from exc
    if not isinstance(song, dict):
        raise ValueError("song no es un objeto JSON")
    if song.get("id") != str(song_id):
        raise ValueError("song_id no coincide con el id de song")
    return TrackPublished(song_id=song_id, artist_id=artist_id, published_at=published_at, song=song)


async def enqueue(redis: Redis, event: TrackPublished) -> str:
    return await redis.xadd(STREAM, to_fields(event), maxlen=MAXLEN, approximate=True)


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def send_to_dlq(redis: Redis, entry_id: str, fields: dict[str, str], reason: str) -> None:
    """Copia el mensaje a la cola de mensajes muertos con el motivo y su id original."""
    await redis.xadd(DLQ_STREAM, {**fields, "reason": reason, "original_id": entry_id}, maxlen=MAXLEN, approximate=True)
