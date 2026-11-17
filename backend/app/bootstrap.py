"""Inicialización administrativa y copia única del monolito detenido. Solo corre en migrate."""
import asyncio
import os
import tempfile

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL

DOMAINS = {
    "users_playlists": ("USERS_DB_PASSWORD", [
        "users", "refresh_tokens", "composer_requests", "audit_log", "playlists", "playlist_songs",
        "favorites", "follows", "notices_seen", "tapes", "tape_members", "tape_tracks", "tape_invites", "invite_claims",
    ]),
    "catalog": ("CATALOG_DB_PASSWORD", ["artists", "albums", "songs", "import_jobs", "published_events"]),
    "playbacks": ("PLAYBACK_DB_PASSWORD", ["playback_counters", "playback_events", "agg_cursor",
                                           "agg_plays_hourly", "agg_user_plays", "request_metrics"]),
}


def upgrade(database, password):
    url = URL.create("postgresql+asyncpg", database, password, host="postgres", database=database)
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    from app.core.config import get_settings
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.attributes["domain"] = database
    config.set_main_option("version_locations", "migrations/" + database)
    command.upgrade(config, "head")


async def provision(admin, database, password):
    existing = await admin.fetchval("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=$1", database)
    if existing and existing != database:
        raise RuntimeError(f"La base {database} ya tiene otro propietario")
    role = await admin.fetchrow("SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=$1", database)
    if role and any(role.values()):
        raise RuntimeError(f"El rol {database} ya tiene privilegios administrativos")
    if not role:
        literal = await admin.fetchval("SELECT quote_literal($1::text)", password)
        await admin.execute(f"CREATE ROLE {database} LOGIN PASSWORD {literal}")
    if not existing:
        await admin.execute(f"CREATE DATABASE {database} OWNER {database}")
    await admin.execute(f"REVOKE CONNECT ON DATABASE {database} FROM PUBLIC")


async def copy_domain(source, target, tables, legacy):
    async with target.transaction():
        await target.execute("CREATE TABLE IF NOT EXISTS meloxo_cutover (id boolean PRIMARY KEY CHECK (id))")
        if await target.fetchval("SELECT EXISTS (SELECT FROM meloxo_cutover)"):
            return
        for table in tables:
            if await target.fetchval(f'SELECT EXISTS (SELECT FROM "{table}")'):
                raise RuntimeError(f"Destino con datos sin marca de migración: {table}")
            if not legacy:
                continue
            columns = [row[0] for row in await source.fetch(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name=$1 ORDER BY ordinal_position", table)]
            if not columns:
                raise RuntimeError(f"Falta la tabla de origen {table}")
            with tempfile.TemporaryFile() as spool:
                exported = await source.copy_from_table(table, columns=columns, output=spool, format="binary")
                spool.seek(0)
                imported = await target.copy_to_table(table, columns=columns, source=spool, format="binary")
                if exported != imported:
                    raise RuntimeError(f"Conteo diferente al copiar {table}")
        if legacy and "playback_events" in tables:
            sequence = await source.fetchrow("SELECT last_value,is_called FROM playback_events_seq_seq")
            await target.execute("SELECT setval('playback_events_seq_seq',$1,$2)", *sequence)
        await target.execute("INSERT INTO meloxo_cutover VALUES (true)")


async def main():
    source = await asyncpg.connect(host="postgres", user="meloxo", password=os.environ["POSTGRES_PASSWORD"], database="meloxo")
    try:
        await source.execute("SELECT pg_advisory_lock(7251002)")
        await source.execute("REVOKE CONNECT ON DATABASE meloxo FROM PUBLIC")
        for db, (variable, _) in DOMAINS.items():
            await provision(source, db, os.environ[variable])
            await asyncio.to_thread(upgrade, db, os.environ[variable])
        async with source.transaction(isolation="repeatable_read", readonly=True):
            has_version = await source.fetchval("SELECT to_regclass('public.alembic_version')::text")
            legacy = await source.fetchval("SELECT version_num FROM alembic_version") if has_version else None
            if legacy not in (None, "0011", "0012"):
                raise RuntimeError("Actualiza primero el monolito hasta 0011")
            if not legacy and await source.fetchval("SELECT to_regclass('public.users')::text"):
                raise RuntimeError("Origen con datos sin versión de Alembic")
            for db, (variable, tables) in DOMAINS.items():
                target = await asyncpg.connect(host="postgres", user=db, password=os.environ[variable], database=db)
                try:
                    extra = ["catalog_pending_audit"] if db == "catalog" and legacy == "0012" else []
                    await copy_domain(source, target, tables + extra, legacy)
                finally:
                    await target.close()
    finally:
        await source.close()


if __name__ == "__main__":
    asyncio.run(main())
