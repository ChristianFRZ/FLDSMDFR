import os
from functools import lru_cache

# Este servicio no tiene base de datos, pero BaseServiceSettings exige DATABASE_URL: se rellena con un valor
# que nunca se usa. Debe ir antes de importar nada de meloxo_common.config.
os.environ.setdefault("DATABASE_URL", "unused://gateway-auth")

from meloxo_common.config import BaseServiceSettings  # noqa: E402


class Settings(BaseServiceSettings):
    USERS_URL: str = "http://users-playlists:8001"
    APP_VERSION: str = "06-poliglota"


@lru_cache
def get_settings() -> Settings:
    return Settings()
