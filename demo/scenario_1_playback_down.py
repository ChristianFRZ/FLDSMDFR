"""El audio sigue disponible y el historial se recupera después de una caída de Métricas."""
import time
import uuid

from common import COMPOSE, check, compose, new_user, published_songs, run


def scenario():
    listener, _ = new_user("cola")
    song_id = published_songs(listener, 1, source="local")[0]["id"]
    event = {"song_id": song_id, "playback_id": str(uuid.uuid4()), "listened_seconds": 12}
    path = f"/api/songs/{song_id}/stream"
    ticket = listener.ok("POST", path + "-ticket")["ticket"]
    url = path + "?ticket=" + ticket
    status, audio = listener.send("GET", url, None, {"Range": "bytes=0-511"})
    check(status == 206 and len(audio) == 512, "primer tramo de audio")
    service = "playback-metrics-service"
    try:
        compose(COMPOSE, "stop", service)
        for _ in range(2):
            status, body = listener.call("POST", "/api/playbacks", event)
            check(status == 202 and body.get("queued"), "evento aceptado en la cola")
        status, audio = listener.send("GET", url, None, {"Range": "bytes=512-1023"})
        check(status == 206 and len(audio) == 512, "el mismo ticket recibe el siguiente tramo")
    finally:
        compose(COMPOSE, "up", "-d", "--wait", "--no-build", "--no-deps", service)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        history = listener.ok("GET", "/api/playbacks/history")
        if history["total"] == 1 and history["items"][0]["playback_id"] == event["playback_id"]:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("El evento pendiente no llegó al historial")


if __name__ == "__main__":
    run("Escenario 1 · Recuperación de reproducciones", scenario)
