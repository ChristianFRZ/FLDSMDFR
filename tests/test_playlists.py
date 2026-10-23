import time
from fastapi.testclient import TestClient


def test_create_playlist(client: TestClient):
    payload = {
        "user_id": 1,
        "name": "Testing Playlist",
        "description": "Playlist para pruebas de latencia",
    }
    response = client.post("/api/playlists", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Testing Playlist"
    assert data["user_id"] == 1
    assert "id" in data


def test_add_song_to_playlist(client: TestClient):
    # Crear playlist
    p_res = client.post(
        "/api/playlists",
        json={"user_id": 1, "name": "Rock Classics", "description": "Rock list"},
    )
    playlist_id = p_res.json()["id"]

    # Agregar canción 1
    add_res = client.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": 1})
    assert add_res.status_code == 200
    assert "exitosa" in add_res.json()["message"]

    # Idempotencia: re-agregar misma canción no debe fallar
    add_again = client.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": 1})
    assert add_again.status_code == 200


def test_get_playlist_details_under_200ms(client: TestClient):
    # PRD Criterio 3: GET /api/playlists/{id} devuelve canciones y metadatos en formato JSON en menos de 200 ms
    p_res = client.post(
        "/api/playlists",
        json={"user_id": 1, "name": "Speed Test List", "description": "Latency check"},
    )
    playlist_id = p_res.json()["id"]

    client.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": 1})
    client.post(f"/api/playlists/{playlist_id}/songs", json={"song_id": 2})

    start_time = time.perf_counter()
    response = client.get(f"/api/playlists/{playlist_id}")
    latency_ms = (time.perf_counter() - start_time) * 1000

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == playlist_id
    assert len(data["songs"]) == 2
    assert latency_ms < 200.0, f"Latencia excedida: {latency_ms:.2f} ms (debe ser < 200 ms)"


def test_add_nonexistent_song_to_playlist(client: TestClient):
    response = client.post("/api/playlists/1/songs", json={"song_id": 99999})
    assert response.status_code == 400


def test_get_nonexistent_playlist(client: TestClient):
    response = client.get("/api/playlists/99999")
    assert response.status_code == 404
