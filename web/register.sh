#!/bin/sh
# Arranca Nginx y registra esta instancia de `web` en el directorio (Consul) con latido TTL,
# igual que los servicios Python (app/shared/discovery.py). Al recibir SIGTERM se da de baja.
set -u

CONSUL="${FLDSMDFR_CONSUL_URL:-http://discovery:8500}"
HEARTBEAT="${FLDSMDFR_HEARTBEAT_S:-3}"
TTL="${FLDSMDFR_TTL_S:-10}"
DEREGISTER_AFTER="${FLDSMDFR_DEREGISTER_AFTER:-1m}"
ID="web-$(hostname)"
ADDR=""

address() { hostname -i | awk '{print $1}'; }
register() {
    ADDR="$(address)"
    BODY="{\"ID\":\"$ID\",\"Name\":\"web\",\"Address\":\"$ADDR\",\"Port\":80,\"Check\":{\"CheckID\":\"$ID-ttl\",\"TTL\":\"${TTL}s\",\"DeregisterCriticalServiceAfter\":\"$DEREGISTER_AFTER\"}}"
    curl -fsS -X PUT -d "$BODY" "$CONSUL/v1/agent/service/register" >/dev/null 2>&1
}
# Si Docker le cambió la IP al contenedor, se vuelve a registrar (igual que discovery.py).
beat() {
    [ "$(address)" = "$ADDR" ] || register
    curl -fsS -X PUT "$CONSUL/v1/agent/check/pass/$ID-ttl" >/dev/null 2>&1 || register
}
stop() {
    curl -fsS -X PUT "$CONSUL/v1/agent/service/deregister/$ID" >/dev/null 2>&1
    nginx -s quit
    exit 0
}
trap stop TERM INT

nginx -g 'daemon off;' &
register && beat
while true; do
    sleep "$HEARTBEAT" &
    wait $!
    beat
done
