import uuid
from fastapi.testclient import TestClient


def test_playback_under_10_seconds_rejected(client: TestClient):
    # PRD Criterio 1: Se requiere al menos 10 segundos para computar una reproducción
    payload = {
        "playback_id": str(uuid.uuid4()),
        "song_id": 1,
        "user_id": 1,
        "played_duration": 8.5,  # Menor a 10s
    }
    response = client.post("/api/playbacks", json=payload)
    assert response.status_code == 422
    assert "umbral mínimo requerido" in response.json()["detail"]


def test_playback_valid_and_idempotency(client: TestClient):
    playback_uuid = str(uuid.uuid4())
    payload = {
        "playback_id": playback_uuid,
        "song_id": 2,
        "user_id": 1,
        "played_duration": 12.0,  # Mayor a 10s
    }

    # 1. Primer envío: debe registrarse y contar (+1)
    res1 = client.post("/api/playbacks", json=payload)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["counted"] is True
    initial_count = data1["current_play_count"]
    assert initial_count >= 1

    # 2. Segundo envío (reintento con MISMO UUID): debe ser detectado como duplicado y no incrementar
    res2 = client.post("/api/playbacks", json=payload)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["counted"] is False
    assert data2["current_play_count"] == initial_count
    assert "idempotencia" in data2["message"].lower()

    # 3. Tercer envío con NUEVO UUID: debe volver a contar (+1)
    payload_new = {
        "playback_id": str(uuid.uuid4()),
        "song_id": 2,
        "user_id": 1,
        "played_duration": 15.0,
    }
    res3 = client.post("/api/playbacks", json=payload_new)
    assert res3.status_code == 201
    data3 = res3.json()
    assert data3["counted"] is True
    assert data3["current_play_count"] == initial_count + 1


def test_top_metrics_ordering(client: TestClient):
    # Generar varias reproducciones para la canción 3 para colocarla en la cima
    for _ in range(5):
        client.post(
            "/api/playbacks",
            json={
                "playback_id": str(uuid.uuid4()),
                "song_id": 3,
                "user_id": 2,
                "played_duration": 11.0,
            },
        )

    response = client.get("/api/metrics/top?limit=5")
    assert response.status_code == 200
    top_list = response.json()
    assert len(top_list) > 0

    # Verificar orden descendente
    play_counts = [item["play_count"] for item in top_list]
    assert play_counts == sorted(play_counts, reverse=True)
    # La canción con más reproducciones debe estar de primera
    assert top_list[0]["song_id"] == 3
