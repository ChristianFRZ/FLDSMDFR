"""Pruebas contra el stack levantado (``docker compose up -d --build``). Se omiten con ``-m "not stack"``."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "demo"))
from common import BASE_URL, Api, admin, new_composer, upload_track  # noqa: E402

pytestmark = pytest.mark.stack
METRICS_CONTAINER = "meloxo-playback-metrics-1"


def lower(headers) -> dict:
    return {key.lower(): value for key, value in headers.items()}


def raw_get(path: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(BASE_URL + path, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, lower(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, lower(exc.headers), exc.read()


def docker(*args: str) -> None:
    subprocess.run(["docker", *args], check=True, capture_output=True)


def wait_healthy(container: str, seconds: int = 90) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        out = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Health.Status}}", container], capture_output=True, text=True
        ).stdout.strip()
        if out == "healthy":
            return
        time.sleep(1)
    raise AssertionError(f"{container} no volvió a estar sano")


@pytest.fixture(scope="module")
def admin_api() -> Api:
    return admin()


@pytest.fixture(scope="module")
def track(admin_api) -> tuple[Api, str]:
    composer, _ = new_composer("edge", admin_api)
    song = upload_track(composer, "Pista de edge")
    song_id = song.get("id") or song["song"]["id"]
    composer.ok("POST", f"/api/composer/tracks/{song_id}/publish", {})
    return composer, song_id


def stream_url(api: Api, song_id: str) -> str:
    ticket = api.ok("POST", f"/api/songs/{song_id}/stream-ticket")["ticket"]
    return f"/api/songs/{song_id}/stream?ticket={ticket}"


def test_edge_health():
    status, _, body = raw_get("/api/health")
    assert status == 200 and json.loads(body) == {"status": "ok"}


def test_internal_not_reachable_through_edge():
    assert raw_get("/internal/health")[0] == 404
    assert raw_get("/internal/latency/drain")[0] == 404


def test_range_requests_through_edge(track):
    composer, song_id = track
    for header, expected in (("bytes=500-", 206), ("bytes=-500", 206), ("bytes=999999999-", 416)):
        status, headers, body = raw_get(stream_url(composer, song_id), {"Range": header})
        assert status == expected, f"{header} respondió {status}"
        if expected == 206:
            assert "content-range" in headers and body
            assert headers.get("accept-ranges", "bytes") == "bytes"


def test_dead_service_returns_api_error_json(admin_api):
    try:
        docker("stop", METRICS_CONTAINER)
        status, headers, body = raw_get("/api/metrics/top", {"Authorization": f"Bearer {admin_api.token}"})
        assert status in (502, 503)
        assert headers["content-type"].startswith("application/json")
        assert json.loads(body)["error"]["code"] == "upstream_unavailable"
        # Los demás servicios siguen atendiendo mientras uno está caído.
        assert admin_api.ok("GET", "/api/users/me")["email"]
        assert "items" in admin_api.ok("GET", "/api/songs?size=1")
    finally:
        docker("start", METRICS_CONTAINER)
        wait_healthy(METRICS_CONTAINER)
    deadline = time.time() + 30
    while time.time() < deadline:  # nginx vuelve a resolver el nombre solo
        status, _, _ = raw_get("/api/metrics/top", {"Authorization": f"Bearer {admin_api.token}"})
        if status == 200:
            return
        time.sleep(1)
    raise AssertionError(f"edge no se recuperó: {status}")
