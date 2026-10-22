import uuid
from fastapi.testclient import TestClient


def test_create_user(client: TestClient):
    unique_suffix = uuid.uuid4().hex[:6]
    payload = {
        "username": f"user_{unique_suffix}",
        "email": f"user_{unique_suffix}@unam.mx",
        "full_name": "Test User",
    }
    response = client.post("/api/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert "id" in data


def test_create_duplicate_user(client: TestClient):
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "username": f"dup_{suffix}",
        "email": f"dup_{suffix}@unam.mx",
        "full_name": "Duplicate User",
    }
    res1 = client.post("/api/users", json=payload)
    assert res1.status_code == 201

    # Intento duplicado debe fallar con 400 Bad Request
    res2 = client.post("/api/users", json=payload)
    assert res2.status_code == 400
    assert "ya está registrado" in res2.json()["detail"]


def test_get_user(client: TestClient):
    response = client.get("/api/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "christian"


def test_get_nonexistent_user(client: TestClient):
    response = client.get("/api/users/99999")
    assert response.status_code == 404
