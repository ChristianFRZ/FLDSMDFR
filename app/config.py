"""Configuracion de la aplicacion, leida de variables de entorno FLDSMDFR_*."""

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
    media_dir: Path = Path("/media/audio")
    seed_dir: Path = Path("media/seed")
    max_upload_bytes: int = 20 * 1024 * 1024
    ui_dist_dir: Path = Path("ui/dist")
    admin_email: str
    admin_password: str
    listener_email: str
    listener_password: str


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
