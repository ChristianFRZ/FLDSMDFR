from functools import lru_cache

from meloxo_common.config import BaseServiceSettings


class Settings(BaseServiceSettings):
    CATALOG_URL: str = "http://catalog-streaming:8002"
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    DEMO_PASSWORD: str = ""
    TAPE_MAX_TRACKS: int = 12
    TAPE_MAX_MEMBERS: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
