"""Configuración de catalog-streaming, leída de variables de entorno FLDSMDFR_*."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLDSMDFR_", env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    cookie_name: str = "fldsmdfr_session"
    media_dir: Path = Path("/media/audio")
    seed_dir: Path = Path("media/seed")
    max_upload_bytes: int = 20 * 1024 * 1024
    # Directorio (Consul). Tiempos cortos para clase; ver app/shared/discovery.py.
    consul_url: str = "http://discovery:8500"
    service_name: str = "catalog-streaming"
    service_port: int = 8000
    discovery_enabled: bool = False
    heartbeat_s: float = 3
    ttl_s: int = 10
    deregister_after: str = "1m"
    lb_cache_s: float = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
