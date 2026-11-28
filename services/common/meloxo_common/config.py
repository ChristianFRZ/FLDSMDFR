from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Variables que comparten todos los servicios. Cada servicio la extiende con las suyas."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    # Una clave corta o vacía permitiría falsificar sesiones: HS256 pide al menos 32 caracteres.
    JWT_SECRET: str = Field(min_length=32)
    DISABLE_SCHEDULER: bool = False
    INTERNAL_TIMEOUT_SECONDS: float = 1.5
    AUTH_CACHE_SECONDS: int = 30
    # Vacío desactiva Redis: la cola y la revocación se omiten.
    REDIS_URL: str = "redis://redis:6379/0"
    # Redis aparte para la caché de lectura (LRU, sin persistencia). Vacío desactiva la caché.
    CACHE_REDIS_URL: str = "redis://redis-cache:6379/0"


@lru_cache
def get_base_settings() -> BaseServiceSettings:
    return BaseServiceSettings()
