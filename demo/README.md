# Demo

Escenarios reproducibles del [PRD](../docs/prd.md#14-pruebas-y-demo-de-fallas) y prueba de carga. Cada escenario corre contra `http://localhost:8080`, imprime `PASA` o `FALLA` y, si falla, termina con un código de error.

El número de cada archivo es el del escenario en la sección 14 del PRD. Los escenarios 1 y 2 necesitan servicios separados, así que llegan en las ramas siguientes. El 9 es la [prueba de carga](#prueba-de-carga).

## Antes de empezar

Necesitas la app en marcha con la semilla cargada, y un `.env` con `ADMIN_EMAIL` y `ADMIN_PASSWORD`. Corre esto desde la raíz del repositorio:

```bash
docker compose up -d --build
docker compose exec app python -m seed all
```

## Escenarios

Solo usan la biblioteca estándar de Python, así que no hay nada que instalar. Para correrlos todos, desde la raíz del repositorio:

```bash
for f in demo/scenario_*.py; do python3 "$f" || break; done
```

| Archivo | Qué comprueba |
| --- | --- |
| [`scenario_3_jamendo_down.py`](scenario_3_jamendo_down.py) | Con Jamendo cortado, las pistas locales y los metadatos guardados siguen disponibles, y el audio de Jamendo da `503 jamendo_unavailable` |
| [`scenario_4_idempotency.py`](scenario_4_idempotency.py) | 100 envíos del mismo `playback_id` cuentan una reproducción y suman 99 a `duplicates_discarded` |
| [`scenario_5_tape_full.py`](scenario_5_tape_full.py) | Dos miembros agregan a la vez la pista 12: uno recibe `201` y el otro `409 tape_full`, en 5 rondas |
| [`scenario_6_last_admin.py`](scenario_6_last_admin.py) | Degradar al único administrador activo da `409`, no cambia nada y queda auditado |
| [`scenario_7_permissions.py`](scenario_7_permissions.py) | Un Compositor recibe `403` en pistas ajenas y en `/api/admin/*` |
| [`scenario_8_double_publish.py`](scenario_8_double_publish.py) | Con dos réplicas y pistas vencidas, hay un solo evento `track_published` y un solo aviso por pista |

[`common.py`](common.py) reúne lo que comparten los escenarios: el cliente de la API, las cuentas de prueba y el arranque del overlay. Ese overlay es [`compose.demo.yaml`](../compose.demo.yaml), en la raíz del repositorio, y lo usan los escenarios 3 y 8.

### Lo que hay que saber

- **Los escenarios 3 y 8 recrean el contenedor `app`.** Lo devuelven a su estado normal en el puerto 8080 aunque fallen, pero no los corras mientras alguien usa la app.
- **Cortar Jamendo requiere dos cambios.** `JAMENDO_API_URL` solo cubre la API. El audio sale directo de `prod-1.storage.jamendo.com`, por eso el overlay también apunta ese host a una dirección que no responde.
- **El escenario 6 suspende a los demás administradores** para quedar como único activo, y los reactiva al terminar.
- **El escenario 8 vence las pistas con SQL**, con la app apagada, porque la API rechaza fechas pasadas. Así, las dos réplicas las encuentran al arrancar. Comprueba el resultado, pero no garantiza que ambas hayan consultado en el mismo instante.
- **Quedan usuarios en la base de datos.** Las cuentas `*@escenarios.meloxo.dev` no tienen `is_demo`, así que `seed clear` no las borra. Las pistas que crean los escenarios sí se eliminan al terminar.

## Prueba de carga

Está en [`locustfile.py`](locustfile.py). Locust no es una dependencia del proyecto, así que se instala en un entorno aparte. Desde la raíz del repositorio:

```bash
python3 -m venv /tmp/locust && /tmp/locust/bin/pip install locust
/tmp/locust/bin/locust -f demo/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8080 --only-summary
```

Cada cliente se registra, arma una lista de 20 pistas y después busca, abre su lista y descarga pistas completas. Solo reproduce pistas locales. El primer byte es el tiempo hasta recibir los encabezados de la respuesta de audio.

### Resultado

Corrida del 2026-11-06 sobre una instalación recién reconstruida: 50 clientes durante 2 minutos, 5576 peticiones y 0 fallos.

| Medida | p50 | p95 | Objetivo p95 |
| --- | --- | --- | --- |
| Primer byte de audio | 12 ms | 39 ms | < 500 ms |
| `GET /api/songs` | 36 ms | 71 ms | < 300 ms |
| `GET /api/playlists/{id}` | 27 ms | 66 ms | < 200 ms |

La máquina fue una laptop Intel i7-1165G7 con 8 hilos, 15 GB de RAM y Linux. Locust, la app (un proceso de uvicorn) y PostgreSQL corrieron en ella, así que el resultado no incluye la latencia de una red real. Jamendo quedó fuera de la carga.

Conviene mencionar dos límites al presentar estos datos:

- **No hay 50 conexiones de audio abiertas todo el tiempo.** Los clientes descargan cada pista a toda velocidad y luego esperan de 1 a 3 s. El ritmo total fue de 47 peticiones por segundo, y las pistas de la semilla pesan unos 480 KB.
- **Las cifras incluyen la fase de preparación.** Durante los primeros 45 s, aproximadamente, los clientes se registran y agregan 20 pistas sin pausa, y esas peticiones son más lentas. Locust acumula los percentiles, así que esta corrida no separa por fase los p99, que van de 240 a 390 ms.
