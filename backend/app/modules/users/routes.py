from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.core.auth import CurrentUser, current_user, require_role
from app.core.db import get_session
from app.core.pagination import PageParams, page_body, page_params
from app.modules.users import admin, service
from app.modules.users.schemas import (
    AuditOut,
    ComposerRequestAdminOut,
    ComposerRequestIn,
    ComposerRequestOut,
    LoginIn,
    OptionalReasonIn,
    ProfilePatch,
    ReasonIn,
    RefreshIn,
    RegisterIn,
    RoleIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/api")
is_admin = require_role("admin")


@router.post("/auth/register", response_model=TokenOut, status_code=201)
async def register(data: RegisterIn, session: AsyncSession = Depends(get_session)):
    return await service.register(session, data)


@router.post("/auth/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request, session: AsyncSession = Depends(get_session)):
    client_ip = request.client.host if request.client else "desconocida"
    return await service.login(session, data.email, data.password, client_ip)


@router.post("/auth/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, session: AsyncSession = Depends(get_session)):
    return await service.refresh(session, data.refresh_token)


@router.post("/auth/logout", status_code=204)
async def logout(data: RefreshIn, session: AsyncSession = Depends(get_session)):
    await service.logout(session, data.refresh_token)
    return Response(status_code=204)


@router.get("/users/me", response_model=UserOut)
async def me(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.get_user(session, user.id)


@router.patch("/users/me", response_model=UserOut)
async def edit_me(
    data: ProfilePatch,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.update_profile(session, user.id, data.display_name)


@router.post("/composer-requests", response_model=ComposerRequestOut, status_code=201)
async def create_request(
    data: ComposerRequestIn,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await admin.create_composer_request(session, user.id, user.role, data.message)


@router.get("/composer-requests/mine", response_model=list[ComposerRequestOut])
async def my_requests(user: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await admin.list_my_requests(session, user.id)


@router.get("/admin/composer-requests")
async def list_requests(
    status: str | None = None,
    params: PageParams = Depends(page_params),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    items, total = await admin.list_composer_requests(session, params, status)
    return page_body([ComposerRequestAdminOut.model_validate(i) for i in items], total, params)


@router.post("/admin/composer-requests/{request_id}/approve", response_model=ComposerRequestOut)
async def approve(
    request_id: UUID,
    data: OptionalReasonIn,
    user: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return await admin.approve_request(session, user.id, request_id, data.reason)


@router.post("/admin/composer-requests/{request_id}/reject", response_model=ComposerRequestOut)
async def reject(
    request_id: UUID,
    data: ReasonIn,
    user: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return await admin.reject_request(session, user.id, request_id, data.reason)


@router.get("/admin/users")
async def list_users(
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    params: PageParams = Depends(page_params),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    items, total = await admin.list_users(session, params, q, role, status)
    return page_body([UserOut.model_validate(i) for i in items], total, params)


@router.post("/admin/users/{user_id}/role", response_model=UserOut)
async def change_role(
    user_id: UUID,
    data: RoleIn,
    user: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return await admin.set_role(session, user.id, user_id, data.role)


@router.post("/admin/users/{user_id}/suspend", response_model=UserOut)
async def suspend(
    user_id: UUID,
    data: OptionalReasonIn,
    user: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return await admin.suspend(session, user.id, user_id, data.reason)


@router.post("/admin/users/{user_id}/reactivate", response_model=UserOut)
async def reactivate(
    user_id: UUID,
    user: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return await admin.reactivate(session, user.id, user_id)


@router.get("/admin/audit")
async def audit(
    action: str | None = None,
    actor_id: UUID | None = None,
    target_id: str | None = None,
    params: PageParams = Depends(page_params),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    items, total = await admin.list_audit(session, params, action, actor_id, target_id)
    return page_body([AuditOut.model_validate(i) for i in items], total, params)
