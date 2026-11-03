"""Configuración de playback-metrics, leída de variables de entorno FLDSMDFR_*."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLDSMDFR_", env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    cookie_name: str = "fldsmdfr_session"
    catalog_url: str = "http://catalog-streaming:8000"
    users_url: str = "http://users-playlists:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
