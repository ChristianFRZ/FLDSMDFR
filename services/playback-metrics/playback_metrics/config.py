from functools import lru_cache

from meloxo_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    CATALOG_URL: str = "http://catalog-streaming:8002"
    USERS_URL: str = "http://users-playlists:8001"
    APP_VERSION: str = "04-resiliencia-concurrencia"
    MEDIA_DIR: str = "/media"


@lru_cache
def get_settings() -> Settings:
    return Settings()
