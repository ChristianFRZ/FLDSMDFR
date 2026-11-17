import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine, session_scope
from app.core.errors import register_error_handlers
from app.core.internal import routers, transport_lifespan
from app.core.scheduler import periodic
from app.modules.analytics.latency import LatencyMiddleware, flush_latency


def service_app(owner, public_routers, jobs=(), startup=None, shutdown=None):
    @asynccontextmanager
    async def lifespan(app):
        if startup:
            await startup()
        tasks = []
        if not get_settings().DISABLE_SCHEDULER:
            tasks = [periodic("latencia", 30, flush_latency)]
            tasks.extend(periodic(*job) for job in jobs)
        try:
            async with transport_lifespan():
                yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if shutdown:
                await shutdown()
            await get_engine().dispose()

    app = FastAPI(title=f"MELOXO · {owner}", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
    register_error_handlers(app)
    app.add_middleware(LatencyMiddleware)
    for router in (*public_routers, routers[owner]):
        app.include_router(router)

    @app.get("/api/health")
    async def health():
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app
