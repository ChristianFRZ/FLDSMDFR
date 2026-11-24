# Semilla de demo

Llena una instalación con catálogo real de Jamendo y actividad simulada. Es un comando aparte: ningún servicio lo ejecuta al arrancar. Habla por HTTP con las rutas `/internal/demo/*` de los tres servicios, que solo existen dentro de la red de Docker (nginx no las publica), así que corre como un contenedor más de Compose.

```bash
docker compose run --rm seed python -m seed all
```

El servicio `seed` está en el perfil `tools`: `docker compose up` no lo levanta. Espera a que los tres servicios estén sanos y comparte con `catalog-streaming` el volumen `media`, donde deja los tonos de las pistas locales.

## Antes de correrla

- La pila tiene que estar arriba y sana: `users-playlists`, `catalog-streaming` y `playback-metrics`.
- El catálogo tiene que estar poblado y alcanzable. Las playlists y los casetes piden pistas a `catalog-streaming` (`get_songs`), por eso la semilla siempre trabaja el catálogo antes que ellos.
- `all` y `catalog` necesitan `JAMENDO_CLIENT_ID` en `.env` (lo usa `catalog-streaming`, no la semilla). Sin él la importación falla con el error de Jamendo; `activity` sí funciona, con las pistas locales.
- Las inserciones de demo no son idempotentes. Si una corrida falla a medias, corre `clear` y vuelve a empezar. `all`, `activity` y `users` ya empiezan borrando lo simulado, así que repetirlas completas es seguro.

## Subcomandos

| Subcomando | Qué hace |
| --- | --- |
| `all` | Ejecuta `catalog` y después `activity` |
| `catalog` | Importa 200 pistas por género, 2,000 en total. Si ya se importaron, no vuelve a pedirlas |
| `activity` | Borra lo simulado y lo crea de nuevo: cuentas, pistas locales, casetes, playlists y 90 días de reproducciones |
| `users` | Borra lo simulado y crea solo las cuentas ficticias |
| `clear` | Borra todo lo simulado y los tonos generados. Las pistas de Jamendo y los usuarios reales se conservan |

Al terminar, imprime tres cuentas de ejemplo: `oyente00@demo.meloxo.dev`, `compositor00@demo.meloxo.dev` y `admin00@demo.meloxo.dev`. La contraseña es `DEMO_PASSWORD` de `.env`; si está vacía, se genera una al azar y se imprime en la terminal. Si un servicio contesta con error, se imprime su código y su mensaje, y el comando sale con error.

## Orden de las llamadas

| Paso | Servicio | Ruta |
| --- | --- | --- |
| 1 | `catalog-streaming` | `GET import-done` y, si falta, `POST catalog/import` |
| 2 | los tres | Borrado previo, en el orden de `clear` |
| 3 | `users-playlists` | `POST users` |
| 4 | `catalog-streaming` | `POST catalog` y `GET catalog/listenable` |
| 5 | `users-playlists` | `POST playlists` y `POST social` |
| 6 | `playback-metrics` | `POST playbacks` y `POST aggregates/catch-up` |

`clear` va al revés: `GET users/ids`, `social/clear`, `playlists/clear`, `playbacks/clear`, `catalog/clear`, `users/clear` y `aggregates/rebuild`.

## Configuración

| Variable | Valor por omisión | Para qué sirve |
| --- | --- | --- |
| `USERS_URL` | `http://users-playlists:8001` | Dirección de `users-playlists` |
| `CATALOG_URL` | `http://catalog-streaming:8002` | Dirección de `catalog-streaming` |
| `PLAYBACK_URL` | `http://playback-metrics:8003` | Dirección de `playback-metrics` |
| `MEDIA_DIR` | `/media` | Volumen compartido con `catalog-streaming` |
| `DEMO_PASSWORD` | al azar | Contraseña de las cuentas ficticias |

Las peticiones esperan hasta 15 minutos: la importación de Jamendo y las inserciones masivas tardan mucho más que el límite de 3 s entre servicios.

## Archivos

| Archivo | Para qué sirve |
| --- | --- |
| [`__init__.py`](__init__.py) | Tamaños de los datos y orden de los pasos |
| [`__main__.py`](__main__.py) | Línea de comandos |
| [`internal.py`](internal.py) | Un cliente HTTP por servicio (`users()`, `catalog()`, `playback()`) |
| [`catalog.py`](catalog.py) | Importación de Jamendo |
| [`users.py`](users.py) | Cuentas ficticias |
| [`activity.py`](activity.py) | Pistas locales, casetes, playlists y reproducciones |
| [`audio.py`](audio.py) | Tonos con `ffmpeg` |
| [`Dockerfile`](Dockerfile) | Imagen con `httpx`, `mutagen` y `ffmpeg` |
| [`pyproject.toml`](pyproject.toml) | Dependencias |

Las pruebas están en [`tests/`](tests/README.md).
