import os
from pathlib import Path

# Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = Path(os.getenv("FLDSMDFR_MEDIA_DIR", BASE_DIR / "media" / "audio"))
DB_PATH = Path(os.getenv("FLDSMDFR_DB_PATH", BASE_DIR / "db" / "fldsmdfr.db"))

# Configuración del servidor
SERVER_HOST = os.getenv("FLDSMDFR_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("FLDSMDFR_PORT", "8000"))

# Configuración de negocio (PRD)
# Mínimo de segundos para computar una reproducción válida
MIN_PLAYBACK_SECONDS = float(os.getenv("FLDSMDFR_MIN_PLAYBACK_SECONDS", "10.0"))

# Tamaño de chunk para streaming parcial si no se especifica rango final
DEFAULT_CHUNK_SIZE = 1024 * 512  # 512 KB
