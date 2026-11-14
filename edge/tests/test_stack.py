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
from common import BASE_URL, COMPOSE, SERVICE, Api, admin, compose, failed, new_composer, new_user, probe_status, restore_catalog, upload_track, wait_edge  # noqa: E402
from scenario_2_failover import wait_healthy as wait_replicas  # noqa: E402

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


# --- gateway-auth: sesión y rol en el edge ---


@pytest.fixture(scope="module")
def listener() -> Api:
    return new_user("gw-listener")[0]


def bearer(api: Api) -> dict:
    return {"Authorization": f"Bearer {api.token}"}


def error_of(body: bytes) -> dict:
    return json.loads(body)["error"]


def test_no_token_is_401_from_the_gateway():
    status, headers, body = raw_get("/api/songs")
    assert status == 401
    assert headers["content-type"].startswith("application/json")
    assert error_of(body)["detail"] == {"source": "gateway"}


def test_listener_gets_403_from_the_gateway_on_admin_and_composer(listener, track):
    for path in ("/api/admin/audit", "/api/composer/tracks"):
        status, _, body = raw_get(path, bearer(listener))
        assert status == 403, path
        assert error_of(body)["detail"]["source"] == "gateway", path
    composer, _ = track
    status, _, body = raw_get("/api/admin/audit", bearer(composer))
    assert status == 403
    assert error_of(body)["detail"]["source"] == "gateway"


def test_composer_reaches_composer_routes(track):
    composer, _ = track
    assert raw_get("/api/composer/tracks", bearer(composer))[0] == 200


def test_admin_reaches_admin_routes(admin_api):
    assert raw_get("/api/admin/audit", bearer(admin_api))[0] == 200
    assert raw_get("/api/composer/tracks", bearer(admin_api))[0] == 200


def test_stream_ticket_is_rejected_as_a_session(track):
    composer, song_id = track
    ticket = composer.ok("POST", f"/api/songs/{song_id}/stream-ticket")["ticket"]
    status, _, body = raw_get("/api/playlists", {"Authorization": f"Bearer {ticket}"})
    assert status == 401
    assert error_of(body)["detail"] == {"source": "gateway"}


def test_fake_identity_headers_do_not_grant_access(listener):
    fake = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-User-Role": "admin"}
    assert raw_get("/api/admin/audit", fake)[0] == 401
    status, _, body = raw_get("/api/admin/audit", {**fake, **bearer(listener)})
    assert status == 403
    assert error_of(body)["detail"]["source"] == "gateway"


def test_empty_required_roles_header_from_client_is_403(listener):
    status, _, body = raw_get("/api/admin/audit", {**bearer(listener), "X-Required-Roles": ""})
    assert status == 403
    assert error_of(body)["detail"]["source"] == "gateway"


def test_gateway_auth_down_is_503(listener, track):
    composer, song_id = track
    url = stream_url(composer, song_id)
    try:
        docker("stop", "meloxo-gateway-auth-1")
        status, headers, body = raw_get("/api/songs", bearer(listener))
        assert status == 503
        assert headers["content-type"].startswith("application/json")
        assert error_of(body)["code"] == "upstream_unavailable"
        # Las rutas públicas no dependen del gateway.
        assert raw_get("/api/health")[0] == 200
        assert raw_get(url, {"Range": "bytes=0-1023"})[0] == 206
    finally:
        in_error = sys.exc_info()[1] is not None
        try:
            docker("start", "meloxo-gateway-auth-1")
            wait_healthy("meloxo-gateway-auth-1")
        except Exception as exc:
            if not in_error:
                raise
            print(f"AVISO: no se pudo restaurar gateway-auth: {exc}", file=sys.stderr)
    deadline = time.time() + 30
    while time.time() < deadline:
        status = raw_get("/api/songs", bearer(listener))[0]
        if status == 200:
            return
        time.sleep(1)
    raise AssertionError(f"el gateway no se recuperó: {status}")


def test_range_still_works_through_the_gateway(track):
    composer, song_id = track
    status, headers, body = raw_get(stream_url(composer, song_id), {"Range": "bytes=0-1023"})
    assert status == 206
    assert headers["content-range"].startswith("bytes 0-1023/")
    assert len(body) == 1024
    assert headers.get("accept-ranges", "bytes") == "bytes"
    for header in ("bytes=500-", "bytes=-500"):
        status, headers, body = raw_get(stream_url(composer, song_id), {"Range": header})
        assert status == 206 and "content-range" in headers and body, header
    assert raw_get(stream_url(composer, song_id), {"Range": "bytes=999999999-"})[0] == 416


def test_replica_failover_loses_at_most_one_request(listener):
    ids = compose(COMPOSE, "ps", "-q", SERVICE).split()
    assert len(ids) >= 2, "hacen falta dos réplicas de catalog-streaming"
    statuses: list[int] = []
    try:
        for index in range(120):
            if index == 40:
                docker("stop", ids[0])
            statuses.append(probe_status(listener, "/api/songs?size=1"))
        assert failed(statuses) <= 1, f"{failed(statuses)} fallidas: {statuses}"
        assert all(status == 200 for status in statuses[-40:])
    finally:
        restore_catalog(wait=lambda: (wait_edge(), wait_replicas()))
