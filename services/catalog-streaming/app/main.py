from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.internal_router import router as internal_router
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.upload_guard import UploadSizeGuard
from app.shared.deps import get_session
from app.shared.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="FLDSMDFR · catalog-streaming", docs_url="/docs")
    register_error_handlers(app)
    app.add_middleware(UploadSizeGuard)
    app.include_router(catalog_router)
    app.include_router(internal_router)

    @app.get("/api/health")
    async def health(session: AsyncSession = Depends(get_session)):
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "degraded", "database": "error"}, status_code=503)
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
