from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.playlists.router import invites_router
from app.modules.playlists.router import router as playlists_router
from app.modules.social.router import router as social_router
from app.modules.users.internal_router import router as users_internal_router
from app.modules.users.router import router as users_router
from app.shared import discovery
from app.shared.deps import get_session
from app.shared.errors import register_error_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.discovery_enabled:
        await discovery.register(settings.service_name, settings.service_port)
    yield
    if settings.discovery_enabled:
        await discovery.deregister()


def create_app() -> FastAPI:
    app = FastAPI(title="FLDSMDFR · users-playlists", docs_url="/docs", lifespan=lifespan)

    @app.middleware("http")
    async def x_instancia(request: Request, call_next):
        """Cada respuesta dice qué instancia contestó (para ver el balanceo)."""
        response = await call_next(request)
        response.headers["X-Instancia"] = discovery.instance_id()
        return response

    register_error_handlers(app)
    app.include_router(users_router)
    app.include_router(playlists_router)
    app.include_router(invites_router)
    app.include_router(social_router)
    app.include_router(users_internal_router)

    @app.get("/api/health")
    async def health(session: AsyncSession = Depends(get_session)):
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "degraded", "database": "error"}, status_code=503)
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
