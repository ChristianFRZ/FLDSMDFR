#!/usr/bin/env bash
# Demo de 04-resiliencia: timeouts, reintento en otra réplica, circuit breaker y degradación.
#
#   ./scripts/demo-04.sh          # todo el recorrido (unos 2 minutos)
#
# Abre la Cabina (http://localhost:8000/cabina, como administrador) mientras corre: la tarjeta
# "Resiliencia" muestra el circuito pasando de cerrado a abierto, semiabierto y cerrado.
# Requiere el sistema arriba (docker compose up --build -d) y curl + python3 en el host.
set -euo pipefail

GW="${GW:-http://localhost:8000}"
CONSUL="${CONSUL:-http://localhost:8500}"
OYENTE="$(mktemp)"
ADMIN="$(mktemp)"
trap 'rm -f "$OYENTE" "$ADMIN"' EXIT

paso() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

vivas() {
  curl -s "$CONSUL/v1/health/service/catalog-streaming?passing=true" \
    | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))'
}

login() {  # login <jar> <correo> <contraseña>
  curl -s -c "$1" -o /dev/null -w "login $2 %{http_code}\n" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$2\",\"password\":\"$3\"}" "$GW/api/auth/login"
}

canciones() {  # código, tiempo e instancia de GET /api/songs (lo balancea el gateway)
  curl -s -b "$OYENTE" -o /dev/null -D - -w '%{http_code} %{time_total}' "$GW/api/songs?limit=1" \
    | tr -d '\r' | awk 'tolower($1)=="x-instancia:"{i=$2} /^[0-9][0-9][0-9] /{c=$1; t=$2}
        END{printf "canciones %s %5.2fs %-32s", c, t, (i?i:"-")}'
}

favoritas() {  # código, tiempo y si vino degradado (users-playlists → catálogo, cliente interno)
  curl -s -b "$OYENTE" -w ' %{http_code} %{time_total}' "$GW/api/me/favorites" \
    | python3 -c '
import sys, json
body, code, t = sys.stdin.read().rsplit(" ", 2)
d = json.loads(body) if code == "200" else {}
estado = "degradadas (copias)" if d.get("degraded") else ("al día" if code == "200" else "-")
print(f"favoritas {code} {float(t):5.2f}s {estado}", end="")'
}

circuito() {  # estado del circuito users-playlists → catalog-streaming
  curl -s -b "$ADMIN" "$GW/api/admin/circuits" | python3 -c '
import sys, json
c = next((c for c in json.load(sys.stdin)["circuits"] if c["target"] == "catalog-streaming"), None)
nombres = {"closed": "cerrado", "open": "abierto", "half_open": "semiabierto"}
if c is None:
    print("circuito: sin llamadas todavía", end="")
else:
    estado, fallas, espera = nombres[c["state"]], c["consecutive_failures"], c["retry_in_s"]
    extra = "" if espera is None else ", vuelve a probar en %.0f s" % espera
    print("circuito %s (%d fallas%s)" % (estado, fallas, extra), end="")'
}

paso "Sesiones: oyente y administrador"
login "$OYENTE" oyente@fldsmdfr.mx oyente12345
login "$ADMIN" admin@fldsmdfr.mx admin12345
PRIMERA="$(curl -s -b "$OYENTE" "$GW/api/songs?limit=1" | python3 -c 'import sys,json; d=json.load(sys.stdin); d=d.get("items", d) if isinstance(d, dict) else d; print(d[0]["id"])')"
curl -s -b "$OYENTE" -o /dev/null -w "favorita %{http_code} (para tener algo que degradar)\n" -X PUT "$GW/api/me/favorites/$PRIMERA"

paso "1. Las tres réplicas contestan en round-robin (réplicas vivas: $(vivas))"
for _ in $(seq 6); do canciones; echo; done

VICTIMA="$(docker compose ps -q catalog-streaming | head -1)"
NOMBRE="$(docker inspect --format '{{.Name}}' "$VICTIMA" | tr -d /)"

paso "2. docker kill $NOMBRE: en 03 había esperas de ~7 s y 503; ahora se reintenta en otra réplica"
docker kill "$VICTIMA" >/dev/null
INICIO=$(date +%s)
for _ in $(seq 15); do
  printf 't=%2ss  %s | %s\n' "$(( $(date +%s) - INICIO ))" "$(canciones)" "$(favoritas)"
  sleep 1
done
docker start "$VICTIMA" >/dev/null
for _ in $(seq 30); do [ "$(vivas)" -ge 3 ] && break; sleep 1; done
echo "La réplica vuelve: réplicas vivas $(vivas)."

paso "3. docker compose stop catalog-streaming (las tres): el circuito se abre a las 5 fallas"
docker compose stop catalog-streaming >/dev/null 2>&1
INICIO=$(date +%s)
for _ in $(seq 8); do
  printf 't=%2ss  %s | %s\n' "$(( $(date +%s) - INICIO ))" "$(favoritas)" "$(circuito)"
  sleep 1
done
echo "Abierto: favoritas responde con sus copias sin llamar al catálogo."

paso "4. docker compose start catalog-streaming: semiabierto → una prueba → cerrado"
docker compose start catalog-streaming >/dev/null 2>&1
INICIO=$(date +%s)
for _ in $(seq 20); do
  # Primero el estado (para ver el semiabierto antes de que la consulta haga la prueba).
  ANTES="$(circuito)"
  printf 't=%2ss  %s | %s | réplicas vivas %s\n' "$(( $(date +%s) - INICIO ))" "$ANTES" "$(favoritas)" "$(vivas)"
  case "$ANTES" in *cerrado*) [ "$(vivas)" -ge 3 ] && break ;; esac
  sleep 1
done

paso "5. Las transiciones, tal como quedaron en el log de users-playlists"
docker compose logs --no-log-prefix users-playlists 2>/dev/null | grep 'circuito ' | tail -6
