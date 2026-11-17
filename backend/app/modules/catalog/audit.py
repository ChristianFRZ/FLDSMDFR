"""La acción de catálogo y su anotación pendiente se confirman juntas."""
import logging
from uuid import uuid4

from sqlalchemy import select

from app.core.db import session_scope
from app.core.errors import AppError
from app.modules.catalog.models import PendingAudit
from app.modules.users.public import record_audit


def enqueue(session, actor_id, action, target_type, target_id, detail=None):
    event = PendingAudit(id=uuid4(), payload={
        "actor_id": str(actor_id), "action": action, "target_type": target_type,
        "target_id": str(target_id), "detail": detail,
    })
    session.add(event)


async def deliver_pending():
    async with session_scope() as session:
        rows = await session.scalars(select(PendingAudit).limit(50).with_for_update(skip_locked=True))
        for event in rows:
            try:
                await record_audit(**event.payload, event_id=event.id)
            except AppError:
                logging.getLogger(__name__).warning("Auditoría pendiente %s", event.id)
                break
            await session.delete(event)
