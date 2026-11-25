"""Con playback-metrics detenido, escuchar y navegar sigue, las reproducciones se encolan (202) y se aplican al volver; solo fallan las métricas."""
import time
import uuid

from common import COMPOSE, Api, admin, check, compose, error_code, new_user, published_songs, run, wait_edge, wait_until

METRICS = "playback-metrics"
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
    raise TimeoutError(f"{METRICS} no volvió en {WAIT_SECONDS} s")


def scenario() -> None:
    boss = admin()
    listener, _ = new_user("metricas")
    song = published_songs(boss, 1)[0]
    plays = [{"playback_id": str(uuid.uuid4()), "song_id": song["id"], "listened_seconds": 30} for _ in range(3)]

    def everything_works() -> None:
        check(listener.call("GET", "/api/songs")[0] == 200, "GET /api/songs responde 200")
        status, audio = listener.stream(song["id"])
        check(status == 206 and len(audio) == 1024, "el audio con Range responde 206")
        check(listener.call("GET", "/api/playlists")[0] == 200, "GET /api/playlists responde 200")

    everything_works()
    check(boss.call("GET", "/api/metrics/top")[0] == 200, "con el servicio arriba, GET /api/metrics/top responde 200")
    try:
        compose(COMPOSE, "stop", METRICS)
        everything_works()
        for play in plays:
            status, data = listener.call("POST", "/api/playbacks", play)
            check(status == 202, f"POST /api/playbacks responde {status}: se encola, no falla")
        check(listener.call("POST", "/api/playbacks", plays[0])[0] == 202, "reenviar la primera también responde 202")
        check_unavailable(boss, "GET", "/api/metrics/top", None, "GET /api/metrics/top")
    finally:
        compose(COMPOSE, "start", METRICS)
    wait_metrics(boss)
    wait_edge()
    wait_until(
        lambda: listener.ok("GET", "/api/playbacks/history")["total"] >= len(plays),
        30,
        "las reproducciones encoladas no se aplicaron en 30 s",
    )
    check(listener.ok("GET", "/api/playbacks/history")["total"] == len(plays), "se aplicaron las 3, sin duplicar la reenviada")
    everything_works()
    check(boss.call("GET", "/api/metrics/top")[0] == 200, "tras arrancar de nuevo, GET /api/metrics/top responde 200")


if __name__ == "__main__":
    run("Escenario 1: playback-metrics caído", scenario)
