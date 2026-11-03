"""Configuración de users-playlists, leída de variables de entorno FLDSMDFR_*."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLDSMDFR_", env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_expire_hours: int = 8
    cookie_name: str = "fldsmdfr_session"
    cookie_secure: bool = False
    # Portadas de casetes en <media_dir>/covers/playlists (volumen propio, no el del catálogo).
    media_dir: Path = Path("/media")
    seed_dir: Path = Path("media/seed")
    admin_email: str
    admin_password: str
    listener_email: str
    listener_password: str

    # Directorio (Consul). Tiempos cortos para clase; ver app/shared/discovery.py.
    consul_url: str = "http://discovery:8500"
    service_name: str = "users-playlists"
    service_port: int = 8000
    discovery_enabled: bool = False
    heartbeat_s: float = 3
    ttl_s: int = 10
    deregister_after: str = "1m"
    lb_cache_s: float = 5

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
