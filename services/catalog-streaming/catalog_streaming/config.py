from functools import lru_cache

from meloxo_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    USERS_URL: str = "http://users-playlists:8001"
    JAMENDO_CLIENT_ID: str = ""
    JAMENDO_API_URL: str = "https://api.jamendo.com/v3.0"
    JAMENDO_AUDIO_MODE: str = "proxy"
    MEDIA_DIR: str = "/media"
    COMPOSER_MAX_TRACKS: int = 20
    UPLOAD_MAX_MP3_MB: int = 15
    UPLOAD_MAX_COVER_MB: int = 2
    UPLOAD_MAX_MINUTES: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
