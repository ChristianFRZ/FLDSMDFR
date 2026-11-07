"""Carga de 50 clientes, solo pistas locales: la red hacia Jamendo no debe entrar en la medición.

Con stream=True, Locust mide hasta que llegan los encabezados: ese tiempo es el primer byte.
"""
import random
import uuid

from locust import HttpUser, between, task

DOMAIN = "escenarios.meloxo.dev"
PLAYLIST_SONGS = 20
CHUNK_BYTES = 64 * 1024
WORDS = ["rock", "love", "night", "demo", "sol", "blue"]


class Listener(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        body = {
            "email": f"carga-{uuid.uuid4().hex[:8]}@{DOMAIN}",
            "password": uuid.uuid4().hex,
            "display_name": "Escenario carga",
        }
        token = self.client.post("/api/auth/register", json=body, name="preparar: registro").json()["access_token"]
        self.client.headers["Authorization"] = f"Bearer {token}"
        page = self.client.get("/api/songs?source=local&size=100", name="preparar: canciones locales").json()
        self.songs = [song["id"] for song in page["items"]]
        if not self.songs:
            raise RuntimeError("No hay pistas locales: corre la semilla primero")
        playlist = self.client.post("/api/playlists", json={"name": "Carga"}, name="preparar: lista").json()
        self.playlist = playlist["id"]
        for song in random.sample(self.songs, min(PLAYLIST_SONGS, len(self.songs))):
            self.client.post(f"/api/playlists/{self.playlist}/songs", json={"song_id": song}, name="preparar: agregar")

    @task(3)
    def search(self) -> None:
        self.client.get(f"/api/songs?q={random.choice(WORDS)}", name="GET /api/songs")

    @task(2)
    def open_playlist(self) -> None:
        self.client.get(f"/api/playlists/{self.playlist}", name="GET /api/playlists/{id}")

    @task(3)
    def listen(self) -> None:
        song = random.choice(self.songs)
        path = f"/api/songs/{song}"
        ticket = self.client.post(f"{path}/stream-ticket", name="POST stream-ticket").json()["ticket"]
        headers = {"Range": "bytes=0-"}
        url = f"{path}/stream?ticket={ticket}"
        response = self.client.get(url, headers=headers, stream=True, name="primer byte")
        for _ in response.iter_content(CHUNK_BYTES):  # el servidor transmite la pista entera, como con un oyente real
            pass
        body = {"playback_id": str(uuid.uuid4()), "song_id": song, "listened_seconds": 30}
        self.client.post("/api/playbacks", json=body, name="POST /api/playbacks")
