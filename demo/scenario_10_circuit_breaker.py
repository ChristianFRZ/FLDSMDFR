"""Con catálogo colgado, el circuit breaker de users-playlists deja de esperar y se recupera al volver.

`docker compose pause` congela las réplicas de catálogo: aceptan la conexión y no responden, que es la
falla lenta que el breaker existe para cortar. El detalle de una playlist pide las pistas a catálogo
(1.5 s de lectura y 2 reintentos), así que mide cuánto tarda cada respuesta.
"""
import time

from common import COMPOSE, SERVICE, admin, check, compose, new_user, published_songs, restore_catalog, run, wait_until

SLOW_SECONDS = 1.4  # una llamada con catálogo colgado espera al menos la lectura de 1.5 s
FAST_SECONDS = 0.5
MAX_CALLS = 10
BREAKER_OPEN_SECONDS = 15


def timed(listener, path: str) -> tuple[float, dict]:
    start = time.monotonic()
    body = listener.ok("GET", path)
    return time.monotonic() - start, body


def scenario() -> None:
    boss = admin()
    listener, _ = new_user("breaker")
    song = published_songs(boss, 1)[0]
    playlist = listener.ok("POST", "/api/playlists", {"name": "Escenario 10"})["id"]
    listener.ok("POST", f"/api/playlists/{playlist}/songs", {"song_id": song["id"]})
    path = f"/api/playlists/{playlist}"
    check(not listener.ok("GET", path)["degraded"], "con catálogo sano, la playlist no está degradada")

    latencies: list[float] = []
    try:
        compose(COMPOSE, "pause", SERVICE)
        for _ in range(MAX_CALLS):
            seconds, body = timed(listener, path)
            latencies.append(seconds)
            check(body["degraded"], "con catálogo colgado, la playlist responde degradada")
            if seconds < FAST_SECONDS:
                break
        check(latencies[0] >= SLOW_SECONDS, f"la primera llamada esperó {latencies[0]:.1f} s")
        check(latencies[-1] < FAST_SECONDS, f"con el breaker abierto responde en {latencies[-1] * 1000:.0f} ms")
        check(len(latencies) <= 7, f"el breaker abrió tras {len(latencies) - 1} llamadas lentas")
    finally:
        compose(COMPOSE, "unpause", SERVICE)
        restore_catalog()

    time.sleep(BREAKER_OPEN_SECONDS + 1)
    wait_until(lambda: not listener.ok("GET", path)["degraded"], 30, "la playlist siguió degradada tras volver catálogo")
    seconds, body = timed(listener, path)
    check(not body["degraded"] and seconds < FAST_SECONDS, "el breaker se cerró y la playlist vuelve completa")


if __name__ == "__main__":
    run("Escenario 10: circuit breaker", scenario)
