from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import BASE_DIR, DB_PATH
from core.module_catalog import catalog_router
from core.module_playback import metrics_router, playbacks_router
from core.module_playlists import playlists_router
from core.module_users import users_router
from db.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos y sembrar datos de prueba si es necesario
    init_database(db_path=DB_PATH, seed=True)
    yield


app = FastAPI(
    title="FLDSMDFR · Monolito de Streaming Musical",
    description=(
        "Sistema centralizado de streaming musical modular para la materia de Sistemas Distribuidos (FI-UNAM). "
        "Fase 01-monolito: Aplicación única con módulos acoplados lógicamente y streaming HTTP Range."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Configuración de CORS para clientes web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de routers de los 4 módulos funcionales
app.include_router(users_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(playlists_router, prefix="/api")
app.include_router(playbacks_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")

# Montar directorio estático de la interfaz de usuario (/ui)
UI_DIR = BASE_DIR / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    """Sirve la interfaz web interactiva del monolito."""
    index_file = UI_DIR / "index.html"
    return FileResponse(index_file)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Endpoint de comprobación de salud del monolito."""
    db_exists = Path(DB_PATH).exists()
    return {
        "status": "healthy",
        "phase": "01-monolito",
        "architecture": "modular-monolith",
        "database_connected": db_exists,
    }


if __name__ == "__main__":
    import uvicorn

    from core.config import SERVER_HOST, SERVER_PORT

    uvicorn.run("main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
