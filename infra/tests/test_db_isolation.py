"""Cada servicio usa su propio rol y no puede ni conectarse a la base de otro."""
import os
from pathlib import Path

import asyncpg
import pytest

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# rol -> (base propia, variable con su clave)
ROLES = {
    "users_playlists": "USERS_DB_PASSWORD",
    "catalog": "CATALOG_DB_PASSWORD",
    "playbacks": "PLAYBACKS_DB_PASSWORD",
}


def _password(var: str) -> str:
    """La misma clave que usa docker compose: nunca escrita en un archivo versionado."""
    if value := os.environ.get(var):
        return value
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(f"{var}="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"Falta {var} en .env")


def _connect(user: str, database: str):
    return asyncpg.connect(
        user=user, password=_password(ROLES[user]), database=database, host="localhost", port=5433, timeout=10
    )


@pytest.mark.parametrize("user", list(ROLES))
async def test_each_user_connects_to_its_own_database(user):
    conn = await _connect(user, user)
    try:
        assert await conn.fetchval("select current_database()") == user
    finally:
        await conn.close()


@pytest.mark.parametrize(
    "user,other", [("catalog", "users_playlists"), ("users_playlists", "playbacks"), ("playbacks", "catalog")]
)
async def test_user_cannot_connect_to_another_services_database(user, other):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await _connect(user, other)


async def test_each_user_owns_its_public_schema():
    for user in ROLES:
        conn = await _connect(user, user)
        try:
            await conn.execute("create table _probe (id int)")
            await conn.execute("drop table _probe")
        finally:
            await conn.close()
