from typing import Literal

from fastapi import Depends, Header, Response

from app.core.auth import CurrentUser, current_user
from app.core.errors import AppError
from app.core.config import get_settings
from app.core.service_app import service_app
from app.modules.users.public import ensure_first_admin
from app.modules.users.routes import router as users
from app.modules.playlists import public as playlist_contracts
from app.modules.playlists.routes import router as playlists
from app.modules.social import public as social_contracts
from app.modules.social.routes import router as social
from app.modules.social.tape_routes import router as tapes


async def bootstrap_admin():
    settings = get_settings()
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        await ensure_first_admin(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)


app = service_app("users", (users, playlists, social, tapes), startup=bootstrap_admin)


@app.get("/internal/gateway/authorize", include_in_schema=False)
async def authorize_gateway(
    x_access_policy: Literal["session", "admin", "composer"] = Header(),
    user: CurrentUser = Depends(current_user),
):
    if x_access_policy != "session" and user.role not in {x_access_policy, "admin"}:
        raise AppError(403, "forbidden", "No tienes permiso para esta acción")
    return Response(status_code=204)
