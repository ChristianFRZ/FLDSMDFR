"""`GET /auth` (subpetición `auth_request` de nginx) y `GET /internal/health`."""
from fastapi import APIRouter, Header, Response

from meloxo_common.errors import AppError

from gateway_auth.auth import auth

router = APIRouter()
health_router = APIRouter(prefix="/internal")

_INVALID = "La sesión no es válida o ya venció"


def _bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AppError(401, "invalid_token", _INVALID)
    return token.strip()


@router.get("/auth")
async def check(
    authorization: str | None = Header(None), x_required_roles: str | None = Header(None)
) -> Response:
    token = _bearer_token(authorization)
    try:
        user = await auth.resolve_user(token)
    except (KeyError, ValueError) as exc:  # `sub` ausente o que no es un UUID
        raise AppError(401, "invalid_token", _INVALID) from exc
    allowed = {role.strip() for role in (x_required_roles or "").split(",") if role.strip()}
    if allowed and user.role not in allowed:
        raise AppError(403, "forbidden", "No tienes permiso para esta acción")
    return Response(status_code=204, headers={"X-User-Id": str(user.id), "X-User-Role": user.role})


@health_router.get("/health")
async def health() -> dict:
    return {"status": "up"}
