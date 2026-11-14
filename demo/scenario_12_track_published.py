"""Los avisos de lanzamientos no dependen de que catálogo responda: `track_published` viaja por Redis.

(a) Con catálogo detenido, los avisos ya guardados siguen completos y sin `degraded`.
(b) Con `users-playlists` detenido, el lanzamiento espera en el stream y el aviso aparece al volver.
(c) Un mensaje inválido va a `track_published:dlq` y no atasca a los que vienen después.
"""
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from common import COMPOSE, Api, Failure, admin, check, compose, new_composer, new_user, restore_catalog, run, sql, upload_track, wait_until

USERS = "users-playlists"
CATALOG = "catalog-streaming"
STREAM_WAIT = 60


def redis(*args: str) -> str:
    return compose(COMPOSE, "exec", "-T", "redis", "redis-cli", *args)


def titles(follower: Api) -> list[str]:
    body = follower.ok("GET", "/api/notices")
    check(not body["degraded"], "los avisos no están degradados")
    return [item["song"]["title"] for item in body["items"] if item["type"] == "release"]


def eventually(probe: Callable[[], bool]) -> Callable[[], bool]:
    """Un servicio que acaba de volver puede dar un 502 o cortar la conexión un instante: se sigue esperando."""

    def attempt() -> bool:
        try:
            return probe()
        except (Failure, OSError, subprocess.CalledProcessError):
            return False

    return attempt


def has_title(follower: Api, title: str) -> Callable[[], bool]:
    return eventually(lambda: title in titles(follower))


def publish_now(composer: Api, title: str) -> str:
    song = upload_track(composer, title)
    composer.ok("POST", f"/api/composer/tracks/{song['id']}/publish")
    return song["id"]


def scenario() -> None:
    boss = admin()
    composer, _ = new_composer("lanzamientos", boss)
    follower, _ = new_user("seguidor")
    follower.ok("PUT", f"/api/follows/{composer.ok('GET', '/api/composer/profile')['id']}")

    publish_now(composer, "Escenario 12, A")
    wait_until(has_title(follower, "Escenario 12, A"), STREAM_WAIT, "el lanzamiento A no llegó a los avisos")

    try:
        compose(COMPOSE, "stop", CATALOG)
        check("Escenario 12, A" in titles(follower), "(a) con catálogo detenido, el aviso A sigue ahí")
    finally:
        restore_catalog()

    later = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    song_b = upload_track(composer, "Escenario 12, B", later)["id"]
    try:
        compose(COMPOSE, "stop", USERS)
        sql(f"update songs set publish_at = now() - interval '1 minute' where id = '{song_b}'")
        wait_until(
            eventually(lambda: sql(f"select relayed_at is not null from published_events where song_id = '{song_b}'") == "t"),
            STREAM_WAIT,
            "la pista B no salió al stream en 60 s",
        )
        check(redis("XLEN", "track_published") != "0", "(b) el evento B espera en el stream")
    finally:
        compose(COMPOSE, "start", USERS)
    wait_until(has_title(follower, "Escenario 12, B"), STREAM_WAIT, "el aviso B no apareció al volver users-playlists")

    dead_before = int(redis("XLEN", "track_published:dlq"))
    redis("XADD", "track_published", "*", "song_id", "no-es-un-uuid")
    publish_now(composer, "Escenario 12, C")
    wait_until(has_title(follower, "Escenario 12, C"), STREAM_WAIT, "el aviso C no apareció tras el mensaje inválido")
    check(int(redis("XLEN", "track_published:dlq")) == dead_before + 1, "(c) el mensaje inválido quedó en la cola de mensajes muertos")


if __name__ == "__main__":
    run("Escenario 12: track_published", scenario)
