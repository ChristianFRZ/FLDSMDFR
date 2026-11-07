"""Con Jamendo caído, lo local y lo guardado sigue; el audio de Jamendo da un 503 controlado."""
import time

from common import admin, check, demo_stack, new_composer, published_songs, run, upload_track

MAX_SECONDS = 15


def scenario() -> None:
    boss = admin()
    composer, _ = new_composer("jamendo", boss)
    local = upload_track(composer, "Escenario 3")
    composer.ok("POST", f"/api/composer/tracks/{local['id']}/publish")  # sin fecha queda en borrador
    jamendo = published_songs(boss, 1, "jamendo")[0]
    try:
        with demo_stack() as (url,):
            api = boss.at(url)
            services = {s["name"]: s["status"] for s in api.ok("GET", "/api/admin/health")["services"]}
            check(services["jamendo"] != "up", f"la salud marca Jamendo como {services['jamendo']}")
            check(services["app"] == "up" and services["database"] == "up", "la app y la base siguen arriba")

            check(api.ok("GET", f"/api/songs/{jamendo['id']}")["id"] == jamendo["id"], "los metadatos guardados responden")
            check(api.ok("GET", "/api/songs?source=jamendo")["total"] > 0, "la búsqueda sigue mostrando Jamendo")

            status, audio = api.stream(local["id"])
            check(status == 206 and len(audio) == 1024, "la pista local se reproduce")

            started = time.monotonic()
            status, body = api.send("GET", f"/api/songs/{jamendo['id']}/stream", None, {})
            elapsed = time.monotonic() - started
            check(status == 503, f"la pista de Jamendo responde {status}")
            check(b"jamendo_unavailable" in body, "el error lleva el código jamendo_unavailable")
            check(elapsed < MAX_SECONDS, f"el 503 llega en {elapsed:.1f} s, sin colgar al oyente")
    finally:
        composer.ok("DELETE", f"/api/composer/tracks/{local['id']}")


if __name__ == "__main__":
    run("Escenario 3: Jamendo caído", scenario)
