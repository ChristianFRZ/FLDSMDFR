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
    catalog_url: str = "http://catalog-streaming:8000"
    admin_email: str
    admin_password: str
    listener_email: str
    listener_password: str


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
