"""Reenviar 100 veces el mismo playback_id cuenta una sola reproducción."""
import uuid
from concurrent.futures import ThreadPoolExecutor

from common import admin, check, new_user, published_songs, run

SENDS = 100
THREADS = 10


def scenario() -> None:
    boss = admin()
    listener, _ = new_user("idempotencia")
    song = published_songs(boss, 1)[0]
    before = boss.ok("GET", "/api/metrics/duplicates")["duplicates_discarded"]
    body = {"playback_id": str(uuid.uuid4()), "song_id": song["id"], "listened_seconds": 30}

    with ThreadPoolExecutor(THREADS) as pool:
        results = list(pool.map(lambda _: listener.call("POST", "/api/playbacks", body), range(SENDS)))

    statuses = [status for status, _ in results]
    check(statuses.count(201) == 1, "una sola respuesta 201")
    check(statuses.count(200) == SENDS - 1, f"{SENDS - 1} respuestas 200")
    check(listener.ok("GET", "/api/playbacks/history")["total"] == 1, "el historial tiene una reproducción")
    after = boss.ok("GET", "/api/metrics/duplicates")["duplicates_discarded"]
    check(after - before == SENDS - 1, f"duplicates_discarded subió {after - before}")


if __name__ == "__main__":
    run("Escenario 4: idempotencia de reproducciones", scenario)
