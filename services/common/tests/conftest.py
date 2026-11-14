import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x/y")
os.environ.setdefault("JWT_SECRET", "secreto-de-prueba-de-32-bytes-o-mas-xx")
os.environ["REDIS_URL"] = ""  # sin Redis real: las pruebas usan fakeredis con override_redis
os.environ["CACHE_REDIS_URL"] = ""  # sin caché real: las pruebas instalan fakeredis con override_cache
