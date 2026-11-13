"""Con playback-metrics detenido, escuchar y navegar sigue; solo fallan las métricas, con el error de la API."""
import time
import uuid

from common import COMPOSE, Api, admin, check, compose, error_code, new_user, published_songs, run, wait_edge

SERVICE = "playback-metrics"
WAIT_SECONDS = 60


def check_unavailable(api: Api, method: str, path: str, body: dict | None, label: str) -> None:
    status, data = api.call(method, path, body)
    check(status in (502, 503, 504), f"{label} responde {status}")
    check(error_code(data) == "upstream_unavailable", f"{label} lleva el código upstream_unavailable")


def wait_metrics(boss: Api) -> None:
    limit = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < limit:
        try:
            if boss.call("GET", "/api/metrics/top")[0] == 200:
                return
        except OSError:
            pass
        time.sleep(1)
    raise TimeoutError(f"{SERVICE} no volvió en {WAIT_SECONDS} s")


def scenario() -> None:
    boss = admin()
    listener, _ = new_user("metricas")
    song = published_songs(boss, 1)[0]
    playback = {"playback_id": str(uuid.uuid4()), "song_id": song["id"], "listened_seconds": 30}

    def everything_works() -> None:
        check(listener.call("GET", "/api/songs")[0] == 200, "GET /api/songs responde 200")
        status, audio = listener.stream(song["id"])
        check(status == 206 and len(audio) == 1024, "el audio con Range responde 206")
        check(listener.call("GET", "/api/playlists")[0] == 200, "GET /api/playlists responde 200")

    everything_works()
    check(boss.call("GET", "/api/metrics/top")[0] == 200, "con el servicio arriba, GET /api/metrics/top responde 200")
    try:
        compose(COMPOSE, "stop", SERVICE)
        everything_works()
        check_unavailable(listener, "POST", "/api/playbacks", playback, "POST /api/playbacks")
        check_unavailable(boss, "GET", "/api/metrics/top", None, "GET /api/metrics/top")
    finally:
        compose(COMPOSE, "start", SERVICE)
    wait_metrics(boss)
    wait_edge()
    everything_works()
    check(boss.call("GET", "/api/metrics/top")[0] == 200, "tras arrancar de nuevo, GET /api/metrics/top responde 200")


if __name__ == "__main__":
    run("Escenario 1: playback-metrics caído", scenario)
