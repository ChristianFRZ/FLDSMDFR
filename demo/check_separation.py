"""Comprueba los procesos y permisos del stack activo sin escribir datos."""
import subprocess

from common import COMPOSE, ROOT, admin, check, run

# Usa la conexión efectiva de cada proceso sin imprimir sus credenciales.
CHECK_DATABASE = """
import asyncio
from sqlalchemy import text
from app.core.db import session_scope
async def main():
    async with session_scope() as session:
        current = await session.scalar(text('select current_database()'))
        print(current)
        query = "select datname from pg_database where datname in ('meloxo','users_playlists','catalog','playbacks') and has_database_privilege(current_user, datname,'CONNECT')"
        print(','.join(await session.scalars(text(query))))
asyncio.run(main())
"""


def scenario():
    response = admin().ok("GET", "/api/admin/health")
    states = {s["name"]: s["status"] for s in response["services"]}
    for service, db in (("users-playlists-service", "users_playlists"), ("catalog-streaming-service", "catalog"),
                        ("playback-metrics-service", "playbacks")):
        check(states.get(service) == "up", f"{service} responde en la red interna")
        result = subprocess.run([*COMPOSE, "exec", "-T", service, "python", "-c", CHECK_DATABASE],
                                cwd=ROOT, capture_output=True, check=True, text=True)
        check(result.stdout.splitlines() == [db, db], f"{service} solo puede conectar a {db} entre las bases de MELOXO")


if __name__ == "__main__":
    run("Separación de servicios y bases", scenario)
