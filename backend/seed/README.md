# Semilla de demo

Llena una instalación con catálogo real de Jamendo y actividad simulada. Es un comando aparte: la app nunca lo ejecuta al arrancar.

Con la app levantada, córrelo desde la raíz del repositorio:

```bash
docker compose exec app python -m seed all
```

Ese `all` se puede cambiar por cualquiera de estos subcomandos:

| Subcomando | Qué hace |
| --- | --- |
| `all` | Ejecuta `catalog` y después `activity` |
| `catalog` | Importa 200 pistas por género, 2,000 en total. Una pista puede llegar en varios géneros, así que quedan menos: 1,789 únicas en la [corrida registrada](../../docs/decisions/01-monolito.md). Si ya se importaron, no vuelve a pedirlas |
| `activity` | Borra lo simulado y lo crea de nuevo: cuentas, pistas locales, casetes, playlists y 90 días de reproducciones |
| `clear` | Borra todo lo simulado y los tonos generados. Las pistas de Jamendo y los usuarios reales se conservan |

Al terminar, la semilla imprime tres cuentas de ejemplo: `oyente00@demo.meloxo.dev`, `compositor00@demo.meloxo.dev` y `admin00@demo.meloxo.dev`. La lista completa está en el [README principal](../../README.md#cuentas-de-acceso). La contraseña es `DEMO_PASSWORD` de `.env`; si está vacía, se genera una al azar y se imprime en la terminal.

## Reglas

- Todo lo simulado lleva `is_demo`. Las pistas de Jamendo son reales y no se marcan.
- Cada [módulo](../app/modules/README.md) escribe sus propios datos en su `demo.py` y los expone en su `public.py`. Aquí no se importan modelos de otros módulos.
- La latencia no se simula: la gráfica muestra peticiones reales, así que se llena al usar la app.
- El audio de las pistas locales son tonos generados con `ffmpeg` en `MEDIA_DIR/demo`. No se guardan en el repositorio.

## Archivos

| Archivo | Para qué sirve |
| --- | --- |
| [`__init__.py`](__init__.py) | Tamaños de los datos y orden de los pasos |
| [`__main__.py`](__main__.py) | Línea de comandos |
| [`catalog.py`](catalog.py) | Importación de Jamendo |
| [`users.py`](users.py) | Cuentas ficticias |
| [`activity.py`](activity.py) | Pistas locales, casetes, playlists y reproducciones |
| [`audio.py`](audio.py) | Tonos con `ffmpeg` |

Las pruebas de la semilla están en [`tests/seed/`](../tests/seed/README.md).
