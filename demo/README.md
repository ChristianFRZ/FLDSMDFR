# Demo

Escenarios reproducibles del [PRD](../docs/prd.md#14-pruebas-y-demo-de-fallas) y prueba de carga. Cada escenario corre contra `http://localhost:8080`, imprime `PASA` o `FALLA` y, si falla, termina con un código de error.

El número de cada archivo es el del escenario en la sección 14 del PRD. El 9 es la [prueba de carga](#prueba-de-carga).

## Antes de empezar

Necesitas el stack en marcha con la semilla cargada, y un `.env` con `ADMIN_EMAIL` y `ADMIN_PASSWORD`. La semilla `all` requiere `JAMENDO_CLIENT_ID`; sin él, `python -m seed activity` carga pistas locales y actividad, y alcanza para todos los escenarios menos el 3, que necesita al menos una pista de Jamendo guardada. Corre esto desde la raíz del repositorio:

```bash
docker compose up -d --build
docker compose run --rm seed python -m seed all
```

## Escenarios

Solo usan la biblioteca estándar de Python, así que no hay nada que instalar. Para correrlos todos, desde la raíz del repositorio:

```bash
for f in demo/scenario_*.py; do python3 "$f"; echo "$f -> código $?"; done
```

Cada escenario termina con código `0` si pasa, `1` si falla y `2` si no se cumple una precondición (por ejemplo, el 3 sin pistas de Jamendo guardadas): en ese caso imprime `PRECONDICIÓN NO CUMPLIDA` y no cuenta como fallo.

| Archivo | Qué comprueba |
| --- | --- |
| [`scenario_1_metrics_down.py`](scenario_1_metrics_down.py) | Con `playback-metrics` detenido, el catálogo, el audio con `Range` y las playlists siguen respondiendo; `POST /api/playbacks` responde `202` (se encola en Redis) y `GET /api/metrics/top` da un error de la API (`upstream_unavailable`). Al arrancarlo, las reproducciones encoladas se aplican, sin duplicar |
| [`scenario_2_failover.py`](scenario_2_failover.py) | Con una réplica de `catalog-streaming` detenida en pleno tráfico (20 peticiones por segundo durante 15 s), el nginx de entrada reintenta con la otra: a lo sumo 1 petición fallida, las últimas 50 dan `200` y la réplica restante recibe el tráfico |
| [`scenario_3_jamendo_down.py`](scenario_3_jamendo_down.py) | Con Jamendo cortado, las pistas locales y los metadatos guardados siguen disponibles, y el audio de Jamendo da `503 jamendo_unavailable` |
| [`scenario_4_idempotency.py`](scenario_4_idempotency.py) | 100 envíos del mismo `playback_id` responden `202` y, ya aplicados por el consumidor, cuentan una reproducción y suman 99 a `duplicates_discarded` |
| [`scenario_5_tape_full.py`](scenario_5_tape_full.py) | Dos miembros agregan a la vez la pista 12: uno recibe `201` y el otro `409 tape_full`, en 5 rondas |
| [`scenario_6_last_admin.py`](scenario_6_last_admin.py) | Degradar al único administrador activo da `409`, no cambia nada y queda auditado |
| [`scenario_7_permissions.py`](scenario_7_permissions.py) | Un Compositor recibe `403` en pistas ajenas y en `/api/admin/*` |
| [`scenario_8_double_publish.py`](scenario_8_double_publish.py) | Con dos réplicas y pistas vencidas, hay un solo evento `track_published` y un solo aviso por pista |
| [`scenario_10_circuit_breaker.py`](scenario_10_circuit_breaker.py) | Con catálogo congelado (`docker compose pause`), el detalle de una playlist tarda al principio más de 1.4 s y sale degradado; tras unas pocas llamadas el circuit breaker abre y responde en menos de 0.5 s. Al volver catálogo y pasar 15 s, la playlist vuelve completa |
| [`scenario_11_revocation.py`](scenario_11_revocation.py) | Un cambio de rol o una suspensión invalida el token anterior en la siguiente petición (menos de 2 s, antes hasta 30 s); un token nuevo trae el rol nuevo de inmediato, y la cuenta suspendida no puede entrar |
| [`scenario_12_track_published.py`](scenario_12_track_published.py) | Con catálogo detenido, los avisos de lanzamientos ya guardados siguen completos y sin `degraded`. Con `users-playlists` detenido, el lanzamiento espera en el stream `track_published` y el aviso aparece al volver. Un mensaje inválido va a `track_published:dlq` y no atasca a los siguientes |

[`common.py`](common.py) reúne lo que comparten los escenarios: el cliente de la API, las cuentas de prueba y el arranque del overlay. Ese overlay es [`compose.demo.yaml`](../compose.demo.yaml), en la raíz del repositorio, y lo usan los escenarios 3 y 8: aplica a `catalog-streaming` el corte de Jamendo y un puerto de host libre por réplica (el 8002 interno), de modo que las réplicas se pueden consultar directo. El nginx de entrada las alcanza por el DNS de Docker. `sql()` recibe la base a consultar (`catalog` por defecto, también `users_playlists` y `playbacks`).

### Lo que hay que saber

- **El escenario 1 detiene `playback-metrics`** y siempre lo arranca de nuevo, aunque falle.
- **El escenario 10 congela `catalog-streaming`** con `docker compose pause`, siempre lo reanuda y lo devuelve a sus dos réplicas, aunque falle. Tarda cerca de un minuto: cada llamada con catálogo colgado espera más de 1.5 s antes de que abra el breaker, y luego espera 15 s a que se cierre.
- **El escenario 12 detiene `catalog-streaming` y `users-playlists`** (cada uno por separado) y los devuelve sanos aunque falle; también deja un mensaje inválido en `track_published:dlq`.
- **El escenario 2 detiene una réplica de `catalog-streaming`** y siempre la restaura (vuelve a las dos réplicas sanas), aunque falle. Para ello usa `restore_catalog`, que también espera a que el 8080 responda.
- **Los escenarios 3 y 8 recrean los contenedores de `catalog-streaming`.** Lo devuelven a sus dos réplicas detrás del 8080 aunque fallen, pero no los corras mientras alguien usa la app.
- **Cortar Jamendo requiere dos cambios.** `JAMENDO_API_URL` solo cubre la API. El audio sale directo de `prod-1.storage.jamendo.com`, por eso el overlay también apunta ese host a una dirección que no responde.
- **El escenario 6 suspende a los demás administradores** para quedar como único activo, y los reactiva al terminar.
- **El escenario 8 vence las pistas con SQL**, con `catalog-streaming` apagado, porque la API rechaza fechas pasadas. Así, las dos réplicas las encuentran al arrancar. Comprueba el resultado, pero no garantiza que ambas hayan consultado en el mismo instante.
- **Un ascenso a Compositor se ve de inmediato** con Redis arriba: la revocación vacía lo que la caché de estado de cuenta sabía de esa persona. Sin Redis tardaría hasta 30 s, y `new_composer` sigue esperando a que `/api/composer/` deje de dar `403` por si acaso.
- **Quedan usuarios en la base de datos.** Las cuentas `*@escenarios.meloxo.dev` no tienen `is_demo`, así que `seed clear` no las borra. Las pistas que crean los escenarios sí se eliminan al terminar.

## Prueba de carga

Está en [`locustfile.py`](locustfile.py). Locust no es una dependencia del proyecto, así que se instala en un entorno aparte. Desde la raíz del repositorio:

```bash
python3 -m venv /tmp/locust && /tmp/locust/bin/pip install locust
/tmp/locust/bin/locust -f demo/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8080 --only-summary
```

Cada cliente se registra, arma una lista de 20 pistas y después busca, abre su lista y descarga pistas completas. Solo reproduce pistas locales. El primer byte es el tiempo hasta recibir los encabezados de la respuesta de audio.

### Resultado

Corrida del 2026-11-13 sobre la rama `03-gateway-balanceo` (gateway con `auth_request` y dos réplicas de catálogo): 50 clientes durante 2 minutos, 5438 peticiones y 0 fallos. Entre paréntesis, la corrida de `02-separacion` (2026-11-12, 5461 peticiones y 0 fallos).

| Medida | p50 | p95 | Objetivo p95 |
| --- | --- | --- | --- |
| Primer byte de audio | 9 ms (9) | 21 ms (20) | < 500 ms |
| `GET /api/songs` | 15 ms (12) | 34 ms (26) | < 300 ms |
| `GET /api/playlists/{id}` | 36 ms (31) | 94 ms (55) | < 200 ms |

La máquina fue una laptop Intel i7-1165G7 con 8 hilos, 15 GB de RAM y Linux. Locust, nginx, `gateway-auth`, los servicios, las dos réplicas de catálogo y PostgreSQL corrieron en ella, así que el resultado no incluye la latencia de una red real. Jamendo quedó fuera de la carga. El análisis está en [`docs/decisions/03-gateway-balanceo.md`](../docs/decisions/03-gateway-balanceo.md#prueba-de-carga-f23), y el de la fase de preparación lenta al agregar a una playlist, en [`02-separacion.md`](../docs/decisions/02-separacion.md#prueba-de-carga-f23).

Conviene mencionar dos límites al presentar estos datos:

- **No hay 50 conexiones de audio abiertas todo el tiempo.** Los clientes descargan cada pista a toda velocidad y luego esperan de 1 a 3 s. El ritmo total fue de unas 45 peticiones por segundo, y las pistas de la semilla pesan unos 480 KB.
- **Las cifras incluyen la fase de preparación.** Durante los primeros 45 s, aproximadamente, los clientes se registran y agregan 20 pistas sin pausa, y esas peticiones son más lentas. Locust acumula los percentiles, así que estas corridas no separan los percentiles por fase. En las ramas 02 y 03 esa fase tuvo p50 de 760 a 780 ms y p95 de 1400 ms al agregar a una playlist; es un aviso por confirmar.
