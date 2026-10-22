from fastapi.testclient import TestClient


def test_list_songs(client: TestClient):
    response = client.get("/api/songs")
    assert response.status_code == 200
    songs = response.json()
    assert len(songs) >= 3
    for s in songs:
        assert "title" in s
        assert "artist" in s
        assert "album" in s
        assert "duration_seconds" in s


def test_search_songs(client: TestClient):
    response = client.get("/api/songs?q=Cyberpunk")
    assert response.status_code == 200
    songs = response.json()
    assert len(songs) == 1
    assert songs[0]["title"] == "Neon Cyberpunk"


def test_stream_full_file(client: TestClient):
    # Solicitud sin cabecera Range debe entregar 200 OK y anunciar Accept-Ranges
    response = client.get("/api/songs/1/stream")
    assert response.status_code == 200
    assert response.headers.get("accept-ranges") == "bytes"
    assert "content-length" in response.headers
    assert len(response.content) > 10000


def test_stream_range_requests(client: TestClient):
    # Solicitud con cabecera Range parcial (primeros 1024 bytes)
    headers = {"Range": "bytes=0-1023"}
    response = client.get("/api/songs/1/stream", headers=headers)

    assert response.status_code == 206
    assert response.headers.get("accept-ranges") == "bytes"
    assert response.headers.get("content-range").startswith("bytes 0-1023/")
    assert response.headers.get("content-length") == "1024"
    assert len(response.content) == 1024


def test_stream_open_ended_range(client: TestClient):
    # Solicitud con rango abierto: desde el byte 5000 hasta el final
    headers = {"Range": "bytes=5000-"}
    response = client.get("/api/songs/1/stream", headers=headers)

    assert response.status_code == 206
    assert response.headers.get("content-range").startswith("bytes 5000-")


def test_stream_invalid_range_out_of_bounds(client: TestClient):
    # Rango fuera de los límites del archivo debe responder 416
    headers = {"Range": "bytes=99999999-999999999"}
    response = client.get("/api/songs/1/stream", headers=headers)
    assert response.status_code == 416
    assert "content-range" in response.headers


def test_stream_nonexistent_song(client: TestClient):
    response = client.get("/api/songs/99999/stream")
    assert response.status_code == 404
