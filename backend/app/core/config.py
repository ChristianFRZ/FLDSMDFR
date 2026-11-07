from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    DEMO_PASSWORD: str = ""
    JAMENDO_CLIENT_ID: str = ""
    JAMENDO_API_URL: str = "https://api.jamendo.com/v3.0"
    JAMENDO_AUDIO_MODE: str = "proxy"
    APP_VERSION: str = "01-monolito"
    DISABLE_SCHEDULER: bool = False
    MEDIA_DIR: str = "/media"
    STATIC_DIR: str = ""
    TAPE_MAX_TRACKS: int = 12
    TAPE_MAX_MEMBERS: int = 8
    COMPOSER_MAX_TRACKS: int = 20
    UPLOAD_MAX_MP3_MB: int = 15
    UPLOAD_MAX_COVER_MB: int = 2
    UPLOAD_MAX_MINUTES: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
