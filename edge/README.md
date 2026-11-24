# edge

Puerta de entrada de MELOXO (puerto `8080`): un nginx que sirve la SPA del `frontend/`, valida la sesión y el rol de cada petición con `gateway-auth` y reparte `/api/*` entre los tres servicios. Los servicios no publican puertos; solo `edge` es alcanzable desde fuera.

## Rutas

nginx elige el `location` con el prefijo más largo. Los prefijos que terminan en `/` evitan que `/api/composer` capture `/api/composer-requests`.

| Servicio | Prefijos |
|---|---|
| `users-playlists` (:8001) | `/api/auth/`, `/api/users/`, `/api/composer-requests`, `/api/admin/composer-requests`, `/api/admin/users`, `/api/admin/audit`, `/api/playlists`, `/api/favorites`, `/api/follows`, `/api/notices`, `/api/releases`, `/api/tapes` |
| `catalog-streaming` (:8002) | `/api/songs`, `/api/artists`, `/api/genres`, `/api/media/`, `/api/composer/`, `/api/admin/catalog`, `/api/admin/songs` |
| `playback-metrics` (:8003) | `/api/playbacks`, `/api/metrics`, `/api/admin/health`, `/api/admin/reports` |
| edge | `/internal/` responde 404; `/api/health` responde `{"status":"ok"}`; el resto de `/api/` responde 404 JSON (`not_found`); todo lo demás es la SPA (`try_files $uri /index.html`) |

## Sesión y rol

Toda ruta pasa por `auth_request /_auth`, que consulta `GET /auth` de `gateway-auth` (:8004) antes de enrutar. Una ruta nueva queda protegida salvo que su `location` lleve `auth_request off;`.

- Sin sesión: `/api/auth/` (register, login, refresh, logout), `/api/health`, `/api/songs/{id}/stream` (usa el ticket de streaming, que valida catálogo), `/api/media/`, el 404 JSON de `/api/` y la SPA.
- Rol por prefijo (`map $uri $required_roles`): `/api/admin/*` exige `admin`; `/api/composer/*` exige `composer` o `admin`; el resto, cualquier sesión válida. El rol se calcula en la petición principal (`$auth_required_roles`), porque dentro de la subpetición `$uri` vale `/_auth`.
- El gateway reenvía `X-User-Id` y `X-User-Role` con lo que respondió `gateway-auth`. En las rutas sin sesión esas variables quedan vacías y nginx no envía la cabecera, así que la que mande el cliente nunca llega al servicio.
- `401` y `403` del gateway responden `edge/errors/unauthorized.json` y `forbidden.json`, con `detail.source = "gateway"`. Si `gateway-auth` no responde, `auth_request` da 500 y `error_page 500 =503` lo devuelve como `503` `upstream_unavailable` (un 500 propio de nginx también se verá como 503). Las rutas sin sesión y la SPA siguen respondiendo.
- Un cambio de rol o una suspensión tarda hasta 30 s en verse (caché de `gateway-auth`, `AUTH_CACHE_SECONDS`): un usuario recién ascendido a Compositor recibe `403` del gateway en `/api/composer/*` hasta que vence.
- Dos detalles de nginx que importan al tocar la configuración: `/_auth` usa su propia variable `$auth_upstream`, porque una subpetición comparte variables con la principal y un `$upstream` compartido enviaría la petición protegida a `gateway-auth`; y el rol exigido se calcula en la petición principal con `if ($uri != /_auth)`, porque dentro de la subpetición `$uri` vale `/_auth`.
- El control de salud es pasivo (nginx de código abierto no sondea): una réplica o un servicio caído se detecta cuando falla una petición.

## Audio y subidas

- `/api/songs/{id}/stream` y `/api/media/`: `proxy_buffering off`, `proxy_request_buffering off`, `proxy_read_timeout 3600s`, `Range` e `If-Range` reenviados y sin gzip.
- `/api/composer/` (MP3 de hasta 15 MB y portadas): `client_max_body_size 20m`. El resto de rutas admite 1 MB.

## Réplicas y failover

`catalog-streaming` corre con dos réplicas (`deploy.replicas: 2` en `compose.yaml`). El DNS de Docker devuelve las dos direcciones para el nombre `catalog-streaming` y nginx reparte entre ellas. En el bloque `server`, `proxy_connect_timeout 1s` (vale para todos los servicios), `proxy_next_upstream error timeout http_502 http_503` y `proxy_next_upstream_tries 2` hacen que una petición que falla en una réplica se pruebe en la otra. Sin `non_idempotent`, nginx no reintenta `POST` ni `PATCH` una vez enviados; `GET`, `HEAD`, `PUT` y `DELETE` sí pueden reintentarse. Es una desviación respecto al diseño, que decía que las escrituras no se reintentan (ver [decisiones](../docs/decisions/03-gateway-balanceo.md)). La prueba [`scenario_2_failover.py`](../demo/scenario_2_failover.py) detiene una réplica en pleno tráfico y [`tests/test_stack.py`](tests/test_stack.py) lo comprueba con el stack arriba.


### Límites del control de salud pasivo

- Tras detener una réplica, durante hasta 10 s (`valid=10s` del resolvedor) cerca de la mitad de las peticiones a catálogo pagan el `proxy_connect_timeout` de 1 s antes de reintentarse con la otra.
- Como `proxy_pass` usa una variable, cada petición forma un upstream implícito nuevo y no hay memoria entre peticiones: `max_fails` y `fail_timeout` no actúan, y una réplica caída se vuelve a probar en cada petición.
- Una réplica colgada (acepta TCP pero nunca responde) se abandona solo tras el `proxy_read_timeout` por defecto de 60 s.

### Ruta normalizada y URI enviada

nginx decide la autenticación con la ruta normalizada, pero `proxy_pass $upstream;` reenvía la URI tal como llegó. Por ejemplo, `/api/media/..%2Fsongs/x/stream` se clasifica como el `location` público del stream y llega a la ruta `/media/{path:path}` de catálogo. Hoy es inofensivo: ambas rutas son públicas y los servicios revalidan por su cuenta. Queda como pendiente menor.

## Servicio caído

nginx resuelve los nombres en cada petición (`resolver 127.0.0.11`, el DNS de Docker, con `proxy_pass` por variable). Por eso arranca aunque un servicio esté caído y lo recupera cuando vuelve. Si un servicio no responde (502, 503 o 504), edge devuelve el JSON de error de la API (`edge/errors/upstream_unavailable.json`) con `Content-Type: application/json`:

```json
{"error":{"code":"upstream_unavailable","message":"Servicio no disponible","detail":null}}
```

## Pruebas

Ver [tests/README.md](tests/README.md).

```bash
.venv/bin/pytest edge/tests -q -m "not stack"
docker compose up -d --build && .venv/bin/pytest edge/tests -q -m stack
```
