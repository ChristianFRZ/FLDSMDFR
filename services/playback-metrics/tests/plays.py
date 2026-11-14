"""Siembra reproducciones como lo hace el consumidor de la cola: con `service.apply_event`."""
from datetime import UTC, datetime
from uuid import UUID, uuid4

from meloxo_common.db import session_scope
from meloxo_common.playback_queue import QueuedEvent
from playback_metrics.modules.playback import service


def _event(kind, user, playback_id, seconds, song_id) -> QueuedEvent:
    return QueuedEvent(kind, UUID(str(user.id)), UUID(str(playback_id)), seconds, song_id, datetime.now(UTC).isoformat())


async def record_play(user, song, seconds: int = 12, playback_id=None) -> str:
    """Devuelve el resultado de `apply_event`: `created` o `duplicate`."""
    event = _event("record", user, playback_id or uuid4(), seconds, song.id)
    async with session_scope() as session:
        return await service.apply_event(session, event)


async def progress_play(user, playback_id, seconds: int) -> str:
    """Devuelve `progress` o `discarded`."""
    async with session_scope() as session:
        return await service.apply_event(session, _event("progress", user, playback_id, seconds, None))
