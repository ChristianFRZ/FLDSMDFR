"""La caché de lectura corre aparte del Redis durable y ningún servicio depende de ella para arrancar."""
from pathlib import Path

import yaml

COMPOSE = yaml.safe_load((Path(__file__).resolve().parents[2] / "compose.yaml").read_text())["services"]
CON_CACHE = ["catalog-streaming", "playback-metrics", "gateway-auth"]


def _command(service: str) -> str:
    command = COMPOSE[service]["command"]
    return " ".join(command) if isinstance(command, list) else command


def test_redis_cache_no_persiste_y_desaloja_lru():
    command = _command("redis-cache")
    assert "--maxmemory 64mb" in command
    assert "--maxmemory-policy allkeys-lru" in command
    assert "--appendonly no" in command
    assert "volumes" not in COMPOSE["redis-cache"]


def test_redis_durable_no_cambia():
    command = _command("redis")
    assert "--appendonly yes" in command
    assert "maxmemory" not in command


def test_servicios_con_cache():
    for name in CON_CACHE:
        env = COMPOSE[name]["environment"]
        assert env["CACHE_REDIS_URL"] == "redis://redis-cache:6379/0", name
        assert "redis-cache" not in COMPOSE[name].get("depends_on", {}), name


def test_users_playlists_no_usa_la_cache():
    assert "CACHE_REDIS_URL" not in COMPOSE["users-playlists"]["environment"]
