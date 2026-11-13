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
    INTERNAL_TIMEOUT_SECONDS: float = 3.0
    AUTH_CACHE_SECONDS: int = 30


@lru_cache
def get_base_settings() -> BaseServiceSettings:
    return BaseServiceSettings()
