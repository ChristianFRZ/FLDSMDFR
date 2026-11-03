#!/usr/bin/env bash
# Demo de 03-gateway-discovery-balanceo: directorio, balanceo y qué pasa cuando muere una réplica.
#
#   ./scripts/demo-03.sh          # todo el recorrido (unos 2 minutos)
#
# Requiere el sistema arriba (docker compose up --build -d) y curl + python3 en el host.
set -euo pipefail

GW="${GW:-http://localhost:8000}"
CONSUL="${CONSUL:-http://localhost:8500}"
JAR="$(mktemp)"
trap 'rm -f "$JAR"' EXIT

paso() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

vivas() {
  curl -s "$CONSUL/v1/health/service/catalog-streaming?passing=true" \
    | python3 -c 'import sys,json; print(" ".join(sorted(e["Service"]["ID"] for e in json.load(sys.stdin))) or "(ninguna)")'
}

instancia() {  # código HTTP e instancia que contestó GET /api/songs
  curl -s -b "$JAR" -o /dev/null -D - -w '%{http_code}' "$GW/api/songs?limit=1" \
    | tr -d '\r' | awk 'tolower($1)=="x-instancia:"{i=$2} /^[0-9][0-9][0-9]$/{c=$1} END{print c, (i?i:"-")}'
}

paso "Sesión de oyente"
curl -s -c "$JAR" -o /dev/null -w 'login %{http_code}\n' -H 'Content-Type: application/json' \
  -d '{"email":"oyente@fldsmdfr.mx","password":"oyente12345"}' "$GW/api/auth/login"

paso "1. El directorio: réplicas vivas de catalog-streaming (panel en $CONSUL)"
vivas

paso "2. Nueve consultas por el gateway: round-robin entre las réplicas"
for _ in $(seq 9); do instancia; done

VICTIMA="$(docker compose ps -q catalog-streaming | head -1)"
NOMBRE="$(docker inspect --format '{{.Name}}' "$VICTIMA" | tr -d /)"

paso "3. docker kill $NOMBRE (muere SIN darse de baja: no manda más latidos)"
docker kill "$VICTIMA" >/dev/null
INICIO=$(date +%s)
for _ in $(seq 20); do
  printf 't=%2ss  %s  | vivas en el directorio: %s\n' "$(( $(date +%s) - INICIO ))" "$(instancia)" "$(vivas)"
  sleep 1
done
echo "Los 503 duran hasta que vence el TTL (10 s) y la caché del balanceador (5 s) se refresca."

paso "4. docker start: la réplica vuelve, se registra y recibe tráfico de nuevo"
docker start "$VICTIMA" >/dev/null
for _ in $(seq 20); do
  [ "$(vivas | wc -w)" -ge 3 ] && break
  sleep 1
done
vivas
sleep 6
for _ in $(seq 6); do instancia; done

paso "5. docker stop $NOMBRE (SIGTERM: se da de baja antes de salir)"
docker stop "$VICTIMA" >/dev/null
INICIO=$(date +%s)
for _ in $(seq 8); do
  printf 't=%2ss  %s  | vivas en el directorio: %s\n' "$(( $(date +%s) - INICIO ))" "$(instancia)" "$(vivas)"
  sleep 1
done
echo "Sin TTL que esperar: solo la caché del balanceador (hasta 5 s) puede mandar alguna petición a la réplica que ya no está."

docker start "$VICTIMA" >/dev/null
paso "Listo: $NOMBRE encendida otra vez"
