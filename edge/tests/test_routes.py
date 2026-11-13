"""Cada ruta pública de los servicios debe resolver, en edge/nginx.conf, a su servicio dueño.

No necesita el stack: importa las aplicaciones de los tres servicios y aplica a mano las reglas
de selección de ``location`` de nginx (exacta, ``^~``, prefijo más largo, expresión regular).
"""
import importlib
import re
from pathlib import Path

import pytest

CONF = Path(__file__).resolve().parents[1] / "nginx.conf"
UPSTREAMS = {
    "users-playlists": "users_playlists.main",
    "catalog-streaming": "catalog_streaming.main",
    "playback-metrics": "playback_metrics.main",
}
LOCATION = re.compile(r"location\s+(?:(=|\^~|~\*|~)\s+)?(\S+)\s*\{")


def blocks() -> list[tuple[str, str, str]]:
    """(modificador, patrón, cuerpo) de cada ``location`` de nginx.conf."""
    text = re.sub(r"#.*", "", CONF.read_text())
    found = []
    for match in LOCATION.finditer(text):
        depth, end = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        found.append((match.group(1) or "", match.group(2), text[match.end() : end - 1]))
    return found


def owner(body: str) -> str | None:
    match = re.search(r"http://([a-z-]+):\d+", body)
    return match.group(1) if match else None


def resolve(path: str) -> tuple[str, str, str] | None:
    """El ``location`` que nginx elegiría para ``path``."""
    locations = blocks()
    for modifier, pattern, body in locations:
        if modifier == "=" and pattern == path:
            return modifier, pattern, body
    prefixes = [b for b in locations if b[0] in ("", "^~") and path.startswith(b[1])]
    best = max(prefixes, key=lambda b: len(b[1]), default=None)
    if best and best[0] == "^~":
        return best
    for modifier, pattern, body in locations:
        flags = re.I if modifier == "~*" else 0
        if modifier in ("~", "~*") and re.search(pattern, path, flags):
            return modifier, pattern, body
    return best


def public_routes() -> list[tuple[str, str]]:
    routes = []
    for service, module in UPSTREAMS.items():
        app = importlib.import_module(module).create_app()
        for path in app.openapi()["paths"]:
            if path.startswith("/api/"):
                routes.append((service, re.sub(r"\{[^}]+\}", "x", path)))
    return routes


ROUTES = public_routes()


def test_routes_were_discovered():
    assert {service for service, _ in ROUTES} == set(UPSTREAMS)
    assert len(ROUTES) > 70
    assert not any(path.startswith("/internal") for _, path in ROUTES)


@pytest.mark.parametrize(("service", "path"), ROUTES)
def test_every_service_route_resolves_to_its_owner(service, path):
    chosen = resolve(path)
    assert chosen is not None, f"{path} no coincide con ningún location"
    assert owner(chosen[2]) == service, f"{path} debería ir a {service}, va a {owner(chosen[2])}"


def test_no_route_resolves_to_two_services():
    """Una ruta pertenece a un solo servicio y ningún servicio la sirve con otro nombre."""
    owners: dict[str, set[str]] = {}
    for service, path in ROUTES:
        owners.setdefault(path, set()).add(service)
    assert {path: s for path, s in owners.items() if len(s) > 1} == {}


def test_composer_requests_are_not_captured_by_composer_prefix():
    assert owner(resolve("/api/composer-requests/mine")[2]) == "users-playlists"
    assert owner(resolve("/api/composer/tracks")[2]) == "catalog-streaming"


def test_internal_prefix_is_blocked():
    modifier, pattern, body = resolve("/internal/health")
    assert (modifier, pattern) == ("^~", "/internal/")
    assert re.search(r"return\s+404\s*;", body)


def test_health_is_answered_by_edge():
    modifier, pattern, body = resolve("/api/health")
    assert (modifier, pattern) == ("=", "/api/health")
    assert "200" in body and '{"status":"ok"}' in body


def test_unknown_paths_fall_back_to_the_spa():
    for path in ("/", "/library", "/playlists/abc"):
        _, pattern, body = resolve(path)
        assert pattern == "/" and "try_files $uri /index.html" in body


def test_unknown_api_paths_are_json_404_not_the_spa():
    for path in ("/api/unknown-thing", "/api/", "/api/auth"):
        modifier, pattern, body = resolve(path)
        assert pattern == "/api/", f"{path} debería caer en /api/, cae en {pattern}"
        assert re.search(r"return\s+404\s", body)
        assert "application/json" in body
        assert '"code":"not_found"' in body and "try_files" not in body


def test_audio_routes_are_not_buffered():
    for path in ("/api/songs/x/stream", "/api/media/a/b.mp3"):
        body = resolve(path)[2]
        assert "proxy_buffering off" in body
        assert "proxy_request_buffering off" in body
        assert "proxy_read_timeout 3600s" in body
        assert "gzip off" in body
        assert "Range" in body and "If-Range" in body


def test_upload_routes_accept_large_bodies():
    for path in ("/api/composer/tracks", "/api/composer/profile/photo"):
        size = re.search(r"client_max_body_size\s+(\d+)m", resolve(path)[2])
        assert size and int(size.group(1)) >= 20


def test_upstream_errors_are_json():
    text = CONF.read_text()
    assert re.search(r"error_page\s+502\s+503\s+504", text)
    assert "application/json" in text
    errors = CONF.parent / "errors"
    body = next(errors.glob("*.json")).read_text()
    assert '"code":"upstream_unavailable"' in body.replace(" ", "")


def test_dns_is_resolved_per_request():
    """Con un ``proxy_pass`` fijo nginx no arranca si un servicio está caído."""
    text = CONF.read_text()
    assert re.search(r"resolver\s+127\.0\.0\.11", text)
    assert not re.search(r"proxy_pass\s+http://", text)
