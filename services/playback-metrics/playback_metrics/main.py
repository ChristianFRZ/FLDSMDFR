import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from meloxo_common.errors import register_error_handlers
from meloxo_common.latency import LatencyMiddleware, internal_router
from meloxo_common.scheduler import periodic

from playback_metrics.config import get_settings
from playback_metrics.internal_routes import router as internal
from playback_metrics.latency_pull import pull_latency, recorder
from playback_metrics.modules.analytics.public import refresh_aggregates
from playback_metrics.modules.analytics.routes import router as analytics_router
from playback_metrics.modules.playback.routes import router as playback_router

PORT = 8003


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    tasks: list[asyncio.Task] = []
    if not get_settings().DISABLE_SCHEDULER:
        tasks = [
            periodic("actualizar_agregados", 2, refresh_aggregates),
            periodic("volcar_latencia", 30, pull_latency),
        ]
    yield
    for task in tasks:
        task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="MELOXO playback-metrics", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
    register_error_handlers(app)
    app.add_middleware(LatencyMiddleware, recorder=recorder)
    app.include_router(playback_router)
    app.include_router(analytics_router)
    app.include_router(internal)
    app.include_router(internal_router(recorder))
    return app


app = create_app()
