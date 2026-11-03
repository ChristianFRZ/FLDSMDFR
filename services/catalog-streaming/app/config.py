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


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
