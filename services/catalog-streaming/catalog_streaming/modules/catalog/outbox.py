"""Relevo del outbox: publica en Redis los `track_published` que `published_events` aún no ha enviado."""
import dataclasses
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from meloxo_common import redis_client, track_events
from meloxo_common.contracts import SongSummary
from meloxo_common.db import session_scope
from catalog_streaming.modules.catalog.models import PublishedEvent, Song
from catalog_streaming.modules.catalog.service import to_summary

log = logging.getLogger(__name__)


async def relay_published_events(batch: int = 100) -> int:
    """Publica hasta `batch` eventos pendientes y marca `relayed_at` solo si el `XADD` salió bien.

    `SKIP LOCKED` reparte los eventos entre procesos. Las pistas de Jamendo, ocultas o borradas solo
    se marcan, sin publicar: igual que `published_since`, no generan avisos. Si Redis falla, la
    transacción se revierte, nada queda marcado y el siguiente ciclo lo reintenta. Devuelve cuántos publicó.
    """
    redis = redis_client.get_redis()
    if redis is None:
        raise RuntimeError("Sin REDIS_URL no se puede relevar track_published")
    published = 0
    async with session_scope() as session:
        pending = (
            await session.execute(
                select(PublishedEvent)
                .where(PublishedEvent.relayed_at.is_(None))
                .order_by(PublishedEvent.published_at)
                .limit(batch)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        if not pending:
            return 0
        found = (await session.execute(select(Song).where(Song.id.in_([e.song_id for e in pending])))).unique().scalars()
        songs = {song.id: song for song in found}
        for event in pending:
            song = songs.get(event.song_id)
            if song is not None and song.status == "published" and song.source == "local":
                await track_events.enqueue(
                    redis,
                    track_events.TrackPublished(
                        song_id=song.id,
                        artist_id=song.artist_id,
                        published_at=event.published_at.isoformat(),
                        song=SongSummary(**dataclasses.asdict(to_summary(song))).model_dump(mode="json"),
                    ),
                )
                published += 1
            event.relayed_at = datetime.now(UTC)
    return published
