import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError, register_error_handlers
from app.core.scheduler import periodic
from app.modules.analytics.latency import LatencyMiddleware, flush_latency
from app.modules.analytics.public import refresh_aggregates
from app.modules.analytics.routes import router as analytics_router
from app.modules.catalog.public import publish_due_tracks, refresh_metadata
from app.modules.catalog.composer_routes import router as composer_router
from app.modules.catalog.routes import router as catalog_router
from app.modules.playback.routes import router as playback_router
from app.modules.playlists.routes import router as playlists_router
from app.modules.social.routes import router as social_router
from app.modules.social.tape_routes import router as tapes_router
from app.modules.users.public import ensure_first_admin
from app.modules.users.routes import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD:
        await ensure_first_admin(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
    tasks: list[asyncio.Task] = []
    if not settings.DISABLE_SCHEDULER:
        tasks = [
            periodic("publicar_programadas", 30, publish_due_tracks),
            periodic("actualizar_agregados", 2, refresh_aggregates),
            periodic("volcar_latencia", 30, flush_latency),
            periodic("refrescar_jamendo", 24 * 3600, refresh_metadata, first_delay=3600),
        ]
    yield
    for task in tasks:
        task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="MELOXO", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(LatencyMiddleware)
    app.include_router(users_router)
    app.include_router(catalog_router)
    app.include_router(composer_router)
    app.include_router(playlists_router)
    app.include_router(playback_router)
    app.include_router(social_router)
    app.include_router(tapes_router)
    app.include_router(analytics_router)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    if get_settings().STATIC_DIR:
        _serve_spa(app, Path(get_settings().STATIC_DIR).resolve())
    return app


def _serve_spa(app: FastAPI, root: Path) -> None:
    """Va al final: atiende lo que ninguna ruta de la API tomó."""

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise AppError(404, "not_found", "Ruta no encontrada")
        target = (root / path).resolve()
        if path and target.is_relative_to(root) and target.is_file():
            return FileResponse(target)
        if path.startswith("assets/"):
            raise AppError(404, "not_found", "Archivo no encontrado")
        return FileResponse(root / "index.html")


app = create_app()
