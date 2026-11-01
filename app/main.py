from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.upload_guard import UploadSizeGuard
from app.modules.playback.router import router as playback_router
from app.modules.playlists.router import invites_router
from app.modules.playlists.router import router as playlists_router
from app.modules.social.router import router as social_router
from app.modules.users.router import router as users_router
from app.shared.deps import get_session
from app.shared.errors import register_error_handlers
from app.spa import mount_spa


def create_app() -> FastAPI:
    app = FastAPI(title="FLDSMDFR", docs_url="/docs")
    register_error_handlers(app)
    app.add_middleware(UploadSizeGuard)
    app.include_router(users_router)
    app.include_router(catalog_router)
    app.include_router(playlists_router)
    app.include_router(invites_router)
    app.include_router(playback_router)
    app.include_router(social_router)

    @app.get("/api/health")
    async def health(session: AsyncSession = Depends(get_session)):
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "degraded", "database": "error"}, status_code=503)
        return {"status": "ok", "database": "ok"}

    # Al final: la ruta comodín del SPA no debe tapar ninguna ruta de la API.
    mount_spa(app, get_settings().ui_dist_dir)
    return app


app = create_app()
