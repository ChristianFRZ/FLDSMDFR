from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from meloxo_common.errors import register_error_handlers
from meloxo_common.latency import LatencyMiddleware, LatencyRecorder, internal_router

from users_playlists.config import get_settings
from users_playlists.internal_routes import router as internal_routes
from users_playlists.modules.playlists.routes import router as playlists_router
from users_playlists.modules.social.routes import router as social_router
from users_playlists.modules.social.tape_routes import router as tapes_router
from users_playlists.modules.users.public import ensure_first_admin
from users_playlists.modules.users.routes import router as users_router

PORT = 8001


def module_for(path: str) -> str | None:
    if path.startswith(("/api/auth", "/api/users", "/api/admin", "/api/composer-requests")):
        return "users"
    if path.startswith("/api/playlists"):
        return "playlists"
    if path.startswith(("/api/favorites", "/api/follows", "/api/notices", "/api/releases", "/api/tapes", "/api/invites", "/api/join", "/api/claims")):
        return "social"
    return None


recorder = LatencyRecorder("users-playlists", module_for)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        await ensure_first_admin(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="MELOXO users-playlists", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(LatencyMiddleware, recorder=recorder)
    app.include_router(users_router)
    app.include_router(playlists_router)
    app.include_router(social_router)
    app.include_router(tapes_router)
    app.include_router(internal_routes)
    app.include_router(internal_router(recorder))
    return app


app = create_app()
