"""Dos réplicas despiertan con pistas vencidas: cada una se publica y se anuncia una sola vez."""
import time
from datetime import UTC, datetime, timedelta

from common import COMPOSE, admin, check, compose, demo_stack, new_composer, new_user, run, sql, upload_track

TRACKS = 10
WAIT_SECONDS = 45


def wait_published(ids: str) -> None:
    limit = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < limit:
        if sql(f"select count(*) from songs where id in ({ids}) and status = 'scheduled'") == "0":
            return
        time.sleep(1)


def scenario() -> None:
    boss = admin()
    composer, _ = new_composer("publicacion", boss)
    follower, _ = new_user("seguidor")
    artist = composer.ok("GET", "/api/composer/profile")
    follower.ok("PUT", f"/api/follows/{artist['id']}")

    later = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    songs = [upload_track(composer, f"Escenario 8, pista {n}", later)["id"] for n in range(TRACKS)]
    ids = ",".join(f"'{song}'" for song in songs)
    try:
        # Con la app apagada vencen todas a la vez, y las dos réplicas las encuentran al arrancar.
        compose(COMPOSE, "stop", "app")
        sql(f"update songs set publish_at = now() - interval '1 minute' where id in ({ids})")

        with demo_stack(replicas=2) as urls:
            check(len(urls) == 2, f"dos réplicas responden: {', '.join(urls)}")
            wait_published(ids)
            published = sql(f"select count(*) from songs where id in ({ids}) and status = 'published'")
            check(published == str(TRACKS), f"{published} de {TRACKS} pistas publicadas")
            events = sql(f"select count(*) from published_events where song_id in ({ids})")
            check(events == str(TRACKS), f"{events} eventos track_published, uno por pista")

            notices = follower.at(urls[1]).ok("GET", "/api/notices")["items"]
            announced = [n["song"]["id"] for n in notices if n["type"] == "release"]
            check(sorted(announced) == sorted(songs), f"el seguidor recibió {len(announced)} avisos, uno por pista")
    finally:
        for song in songs:
            composer.ok("DELETE", f"/api/composer/tracks/{song}")


if __name__ == "__main__":
    run("Escenario 8: doble publicación", scenario)
