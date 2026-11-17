from sqlalchemy import func, select

from app.core.db import session_scope
from app.core.errors import AppError
from app.modules.catalog import audit, publishing
from app.modules.catalog.models import PendingAudit
from app.modules.users.models import AuditEntry


async def test_lost_audit_ack_is_recoverable_and_idempotent(admin, make_song, monkeypatch):
    song = await make_song()
    record = audit.record_audit

    async def lost_ack(**payload):
        await record(**payload)
        raise AppError(503, "service_unavailable", "Se perdió la confirmación")

    with monkeypatch.context() as patch:
        patch.setattr(audit, "record_audit", lost_ack)
        async with session_scope() as session:
            await publishing.hide_song(session, admin.id, song.id, "moderación")
    async with session_scope() as session:
        event_id = (await session.scalars(select(PendingAudit.id))).one()

    await audit.deliver_pending()
    async with session_scope() as session:
        assert await session.get(PendingAudit, event_id) is None
        rows = select(func.count()).select_from(AuditEntry).where(AuditEntry.target_id == str(song.id))
        assert await session.scalar(rows) == 1
        assert (await session.get(AuditEntry, event_id)).action == "hide_song"
