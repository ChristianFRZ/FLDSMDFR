"""Administración de cuentas, solicitudes de Compositor y bitácora."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.core.errors import AppError
from app.core.pagination import PageParams
from app.modules.users.models import AuditEntry, ComposerRequest, User
from app.modules.users.schemas import ComposerRequestOut


async def write_audit(
    actor_id: UUID | None,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict | None = None,
    outcome: str = "ok",
) -> None:
    async with session_scope() as session:
        session.add(
            AuditEntry(
                actor_id=actor_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                outcome=outcome,
            )
        )


async def _lock_active_admins(session: AsyncSession) -> list[UUID]:
    """Serializa los cambios que afectan a administradores. Las filas se bloquean en orden para evitar interbloqueos."""
    query = select(User.id).where(User.role == "admin", User.status == "active").order_by(User.id).with_for_update()
    return list((await session.execute(query)).scalars())


async def _ensure_not_last_admin(session: AsyncSession, target: User, actor_id: UUID, action: str, detail: dict) -> None:
    target_id = target.id  # rollback expira el objeto
    admins = await _lock_active_admins(session)
    await session.refresh(target)
    if actor_id not in admins:
        await session.rollback()
        raise AppError(403, "forbidden", "No tienes permiso para esta acción")
    if target_id in admins and len(admins) <= 1:
        await session.rollback()
        await write_audit(actor_id, action, "user", str(target_id), detail, outcome="rejected")
        raise AppError(409, "last_admin", "Debe quedar al menos un administrador activo")


async def _get_user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "Usuario no encontrado")
    return user


async def set_role(session: AsyncSession, actor_id: UUID, user_id: UUID, role: str) -> User:
    user = await _get_user(session, user_id)
    previous = user.role
    detail = {"from": previous, "to": role}
    if role != "admin":
        await _ensure_not_last_admin(session, user, actor_id, "role_change", detail)
    user.role = role
    await session.commit()
    await write_audit(actor_id, "role_change", "user", str(user.id), detail)
    return user


async def suspend(session: AsyncSession, actor_id: UUID, user_id: UUID, reason: str | None) -> User:
    user = await _get_user(session, user_id)
    detail = {"reason": reason}
    await _ensure_not_last_admin(session, user, actor_id, "suspend", detail)
    user.status = "suspended"
    await session.commit()
    await write_audit(actor_id, "suspend", "user", str(user.id), detail)
    return user


async def reactivate(session: AsyncSession, actor_id: UUID, user_id: UUID) -> User:
    user = await _get_user(session, user_id)
    user.status = "active"
    await session.commit()
    await write_audit(actor_id, "reactivate", "user", str(user.id))
    return user


async def list_users(
    session: AsyncSession, params: PageParams, q: str | None, role: str | None, status: str | None
) -> tuple[list[User], int]:
    filters = []
    if q:
        like = f"%{q}%"
        filters.append(User.email.ilike(like) | User.display_name.ilike(like))
    if role:
        filters.append(User.role == role)
    if status:
        filters.append(User.status == status)
    total = await session.scalar(select(func.count()).select_from(User).where(*filters))
    query = select(User).where(*filters).order_by(User.created_at.desc()).offset(params.offset).limit(params.size)
    return list((await session.execute(query)).scalars()), total or 0


async def list_audit(
    session: AsyncSession,
    params: PageParams,
    action: str | None,
    actor_id: UUID | None,
    target_id: str | None,
) -> tuple[list[AuditEntry], int]:
    filters = []
    if action:
        filters.append(AuditEntry.action == action)
    if actor_id:
        filters.append(AuditEntry.actor_id == actor_id)
    if target_id:
        filters.append(AuditEntry.target_id == target_id)
    total = await session.scalar(select(func.count()).select_from(AuditEntry).where(*filters))
    query = (
        select(AuditEntry)
        .where(*filters)
        .order_by(AuditEntry.created_at.desc(), AuditEntry.id)
        .offset(params.offset)
        .limit(params.size)
    )
    return list((await session.execute(query)).scalars()), total or 0


async def create_composer_request(session: AsyncSession, user_id: UUID, role: str, message: str) -> ComposerRequest:
    if role != "listener":
        raise AppError(409, "already_composer", "Tu cuenta ya puede publicar música")
    request = ComposerRequest(user_id=user_id, message=message)
    session.add(request)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(409, "request_pending", "Ya tienes una solicitud pendiente") from exc
    return request


async def list_my_requests(session: AsyncSession, user_id: UUID) -> list[ComposerRequest]:
    query = select(ComposerRequest).where(ComposerRequest.user_id == user_id)
    return list((await session.execute(query.order_by(ComposerRequest.created_at.desc()))).scalars())


async def list_composer_requests(
    session: AsyncSession, params: PageParams, status: str | None
) -> tuple[list[dict], int]:
    filters = [ComposerRequest.status == status] if status else []
    total = await session.scalar(select(func.count()).select_from(ComposerRequest).where(*filters))
    query = (
        select(ComposerRequest, User.display_name, User.email)
        .join(User, User.id == ComposerRequest.user_id)
        .where(*filters)
        .order_by(ComposerRequest.created_at)
        .offset(params.offset)
        .limit(params.size)
    )
    rows = (await session.execute(query)).all()
    items = [
        {**ComposerRequestOut.model_validate(item).model_dump(), "user_name": name, "user_email": email}
        for item, name, email in rows
    ]
    return items, total or 0


async def _lock_pending(session: AsyncSession, request_id: UUID) -> ComposerRequest:
    query = select(ComposerRequest).where(ComposerRequest.id == request_id).with_for_update()
    request = (await session.execute(query)).scalar_one_or_none()
    if request is None:
        raise AppError(404, "request_not_found", "Solicitud no encontrada")
    if request.status != "pending":
        raise AppError(409, "request_reviewed", "Esta solicitud ya fue revisada")
    return request


async def approve_request(session: AsyncSession, actor_id: UUID, request_id: UUID, reason: str | None) -> ComposerRequest:
    request = await _lock_pending(session, request_id)
    user = await _get_user(session, request.user_id)
    if user.role == "listener":
        user.role = "composer"
    request.status = "approved"
    request.reason = reason
    request.reviewed_by = actor_id
    await session.commit()
    await write_audit(actor_id, "composer_approved", "user", str(user.id), {"reason": reason})
    return request


async def reject_request(session: AsyncSession, actor_id: UUID, request_id: UUID, reason: str) -> ComposerRequest:
    request = await _lock_pending(session, request_id)
    request.status = "rejected"
    request.reason = reason
    request.reviewed_by = actor_id
    await session.commit()
    await write_audit(actor_id, "composer_rejected", "user", str(request.user_id), {"reason": reason})
    return request
