import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.users import service
from app.modules.users.schemas import LoginIn, RegisterIn, RoleIn, TokenOut, UserOut
from app.shared.deps import CurrentUser, current_user, get_session, require_admin
from app.shared.security import create_access_token

router = APIRouter(prefix="/api", tags=["users"])


def _token_response(user: UserOut, response: Response) -> TokenOut:
    settings = get_settings()
    token = create_access_token(user.id, user.role)
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=settings.jwt_expire_hours * 3600,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/",
    )
    return TokenOut(access_token=token, token_type="bearer", user=user)


@router.post("/auth/register", status_code=201, response_model=TokenOut)
async def register(
    data: RegisterIn, response: Response, session: AsyncSession = Depends(get_session)
):
    return _token_response(await service.register(session, data), response)


@router.post("/auth/login", response_model=TokenOut)
async def login(data: LoginIn, response: Response, session: AsyncSession = Depends(get_session)):
    user = await service.authenticate(session, data.email, data.password)
    return _token_response(user, response)


@router.post("/auth/logout", status_code=204)
async def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(get_settings().cookie_name, path="/")
    return response


@router.get("/auth/me", response_model=UserOut)
async def me(
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return await service.get_user(session, user.user_id)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_admin)])
async def list_users(q: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_users(session, q)


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def set_role(
    user_id: uuid.UUID,
    data: RoleIn,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    return await service.set_role(session, admin.user_id, user_id, data.role)
