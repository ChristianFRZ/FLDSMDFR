import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from meloxo_common.errors import register_error_handlers
from meloxo_common.latency import LatencyMiddleware, LatencyRecorder, internal_router
from meloxo_common.scheduler import periodic

from catalog_streaming.config import get_settings
from catalog_streaming.internal_routes import router as internal_routes
from catalog_streaming.modules.catalog.composer_routes import router as composer_router
from catalog_streaming.modules.catalog.public import publish_due_tracks, refresh_metadata, relay_published_events
from catalog_streaming.modules.catalog.routes import router as catalog_router
from catalog_streaming.playback_routes import router as playback_router

PORT = 8002


def module_for(path: str) -> str | None:
    if path.startswith("/api/songs/") and path.endswith("/stream"):
        return "streaming"
    if path.startswith(("/api/songs", "/api/artists", "/api/genres", "/api/media", "/api/composer", "/api/admin")):
        return "catalog"
    return None


recorder = LatencyRecorder("catalog-streaming", module_for)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    tasks: list[asyncio.Task] = []
    if not get_settings().DISABLE_SCHEDULER:
        tasks = [
            periodic("publicar_programadas", 30, publish_due_tracks),
            periodic("relevar_publicaciones", 2, relay_published_events),
            periodic("refrescar_jamendo", 24 * 3600, refresh_metadata, first_delay=3600),
        ]
    yield
    for task in tasks:
        task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="MELOXO catalog-streaming", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(LatencyMiddleware, recorder=recorder)
    app.include_router(catalog_router)
    app.include_router(composer_router)
    app.include_router(playback_router)
    app.include_router(internal_routes)
    app.include_router(internal_router(recorder))
    return app


app = create_app()
