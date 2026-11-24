#!/bin/bash
# Se ejecuta una sola vez, al crear el directorio de datos (docker-entrypoint-initdb.d).
# Crea una base y un rol por servicio; cada rol solo puede conectarse a la suya.
set -euo pipefail

: "${USERS_DB_PASSWORD:?Falta USERS_DB_PASSWORD}"
: "${CATALOG_DB_PASSWORD:?Falta CATALOG_DB_PASSWORD}"
: "${PLAYBACKS_DB_PASSWORD:?Falta PLAYBACKS_DB_PASSWORD}"

create_service_db() {
  local name="$1" password="$2"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -v name="$name" -v password="$password" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'name', :'password') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'name', :'name') \gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'name') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'name', :'name') \gexec
SQL
  # El dueño de la base también lo es del esquema public, para que alembic cree tablas.
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$name" -v name="$name" <<'SQL'
SELECT format('ALTER SCHEMA public OWNER TO %I', :'name') \gexec
SQL
}

create_service_db users_playlists "$USERS_DB_PASSWORD"
create_service_db catalog "$CATALOG_DB_PASSWORD"
create_service_db playbacks "$PLAYBACKS_DB_PASSWORD"

# La búsqueda por similitud del catálogo usa trigramas.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname catalog -c "CREATE EXTENSION IF NOT EXISTS pg_trgm"
