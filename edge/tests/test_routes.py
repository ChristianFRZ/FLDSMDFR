"""Cada ruta pública de los servicios debe resolver, en edge/nginx.conf, a su servicio dueño.

No necesita el stack: importa las aplicaciones de los tres servicios y aplica a mano las reglas
de selección de ``location`` de nginx (exacta, ``^~``, prefijo más largo, expresión regular).
"""
import importlib
import json
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
    body = (errors / "upstream_unavailable.json").read_text()
    assert '"code":"upstream_unavailable"' in body.replace(" ", "")


def test_dns_is_resolved_per_request():
    """Con un ``proxy_pass`` fijo nginx no arranca si un servicio está caído."""
    text = CONF.read_text()
    assert re.search(r"resolver\s+127\.0\.0\.11", text)
    assert not re.search(r"proxy_pass\s+http://", text)


# --- Sesión y rol en el gateway ---

ERRORS = CONF.parent / "errors"
STREAM = r"^/api/songs/[^/]+/stream$"
PUBLIC_LOCATIONS = {"/api/auth/", "/api/health", STREAM, "/api/media/", "/api/", "/"}
AUTH_ROUTES = {"/api/auth/register", "/api/auth/login", "/api/auth/refresh", "/api/auth/logout"}


def strip_comments(text: str) -> str:
    return re.sub(r"#.*", "", text)


def server_level() -> str:
    """El texto del ``server`` sin los cuerpos de sus ``location``."""
    text = strip_comments(CONF.read_text())
    kept, start = [], 0
    for match in LOCATION.finditer(text):
        depth, end = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        kept.append(text[start : match.start()])
        start = end
    return "".join(kept) + text[start:]


def auth_off(body: str) -> bool:
    return re.search(r"auth_request\s+off\s*;", body) is not None


def is_internal(pattern: str, body: str) -> bool:
    return re.search(r"\binternal\s*;", body) is not None or pattern == "/internal/"


def route_security() -> dict[str, bool]:
    """Ruta (con ``{x}`` como ``x``) → si su OpenAPI declara ``security`` en alguna operación."""
    secured: dict[str, bool] = {}
    for module in UPSTREAMS.values():
        app = importlib.import_module(module).create_app()
        for path, operations in app.openapi()["paths"].items():
            if path.startswith("/api/"):
                key = re.sub(r"\{[^}]+\}", "x", path)
                has = any(op.get("security") for op in operations.values() if isinstance(op, dict))
                secured[key] = secured.get(key, False) or has
    return secured


def required_roles(uri: str) -> str:
    """Evalúa ``map $uri $required_roles`` como nginx: la primera regex que coincide, si no ``default``."""
    text = strip_comments(CONF.read_text())
    match = re.search(r"map\s+\$uri\s+\$required_roles\s*\{(.*?)\}", text, re.S)
    assert match, "falta map $uri $required_roles"
    default = ""
    for line in match.group(1).split(";"):
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        key, value = parts[0], parts[1].strip().strip('"')
        if key == "default":
            default = value
        elif key.startswith("~") and re.search(key[1:], uri):
            return value
    return default


def test_auth_request_is_on_by_default():
    assert re.search(r"auth_request\s+/_auth\s*;", server_level())
    _, pattern, body = resolve("/_auth")
    assert pattern == "/_auth" and is_internal(pattern, body)
    assert "http://gateway-auth:8004" in body


def test_public_locations_are_exactly_the_documented_ones():
    public = {pattern for _, pattern, body in blocks() if auth_off(body) and not is_internal(pattern, body)}
    assert public == PUBLIC_LOCATIONS
    for path in AUTH_ROUTES | {"/api/health", "/api/songs/x/stream", "/api/media/a/b.mp3", "/api/nope", "/", "/library"}:
        assert auth_off(resolve(path)[2]), f"{path} debería pasar sin sesión"


def test_public_set_matches_the_services():
    """Lo que el servicio deja sin ``security`` (más el stream, que usa ticket) es lo único sin auth_request."""
    for path, secured in route_security().items():
        public = not secured or path == "/api/songs/x/stream"
        assert auth_off(resolve(path)[2]) == public, f"{path}: pública={public} en el servicio, no en nginx"


def test_role_map():
    assert required_roles("/api/admin/users") == "admin"
    assert required_roles("/api/admin/composer-requests/x") == "admin"
    assert required_roles("/api/composer/tracks") == "composer,admin"
    assert required_roles("/api/composer-requests/mine") == ""
    assert required_roles("/api/playlists") == ""


def test_identity_headers_are_always_set_by_the_gateway():
    server = server_level()
    identity = (r"proxy_set_header\s+X-User-Id\s+\$auth_user_id\s*;", r"proxy_set_header\s+X-User-Role\s+\$auth_user_role\s*;")
    for _, pattern, body in blocks():
        if "proxy_pass" not in body or pattern == "/_auth":
            continue
        source = body if "proxy_set_header" in body else server
        for header in identity:
            assert re.search(header, source), f"{pattern} no fija {header}"
    auth = resolve("/_auth")[2]
    for name in ("X-User-Id", "X-User-Role"):
        assert re.search(rf'proxy_set_header\s+{name}\s+""\s*;', auth), f"/_auth debe vaciar {name}"
    text = strip_comments(CONF.read_text())
    assert text.count("X-Required-Roles") == 1
    assert "X-Required-Roles" in resolve("/_auth")[2]


def test_auth_failures_return_json():
    server = server_level()
    assert re.search(r"error_page\s+401\s+/errors/unauthorized\.json\s*;", server)
    assert re.search(r"error_page\s+403\s+/errors/forbidden\.json\s*;", server)
    assert re.search(r"error_page\s+500\s+=503\s+/errors/upstream_unavailable\.json\s*;", server)
    for name, code in (("unauthorized", "invalid_token"), ("forbidden", "forbidden")):
        _, _, body = resolve(f"/errors/{name}.json")
        assert is_internal("", body) and "application/json" in body and auth_off(body)
        error = json.loads((ERRORS / f"{name}.json").read_text())["error"]
        assert error["code"] == code and error["detail"] == {"source": "gateway"} and error["message"]
    error = json.loads((ERRORS / "upstream_unavailable.json").read_text())["error"]
    assert error["code"] == "upstream_unavailable"


def test_auth_subrequest_does_not_overwrite_the_main_upstream():
    """Una subpetición comparte las variables con la principal: si /_auth hiciera ``set $upstream``,
    la petición protegida acabaría en gateway-auth en vez de en su servicio."""
    body = resolve("/_auth")[2]
    assert not re.search(r"\$upstream\b", body)


def test_required_roles_are_computed_from_the_main_request_uri():
    """En la subpetición ``$uri`` vale ``/_auth``: el ``map`` evaluado ahí siempre daría vacío.
    El rol se fija en el ``server`` para la petición principal y /_auth solo lo reenvía."""
    body = resolve("/_auth")[2]
    sent = re.search(r"proxy_set_header\s+X-Required-Roles\s+(\$\w+)\s*;", body)
    assert sent and sent.group(1) != "$required_roles"
    assert re.search(
        r"if\s*\(\s*\$uri\s*!=\s*/_auth\s*\)\s*\{\s*set\s+" + re.escape(sent.group(1)) + r"\s+\$required_roles\s*;\s*\}",
        server_level(),
    )


# --- Failover hacia la réplica sana ---


def effective(directive: str, body: str) -> str | None:
    """Valor de una directiva ``proxy_*`` en el ``location``, o el del ``server`` si no la repite."""
    for text in (body, server_level()):
        match = re.search(rf"^\s*{directive}\s+([^;]+);", text, re.M)
        if match:
            return match.group(1).strip()
    return None


def test_catalog_locations_fail_over():
    """Failover con dos intentos y sin non_idempotent: POST/PATCH no se repiten (GET, HEAD, PUT y DELETE sí pueden)."""
    catalog = [(p, b) for _, p, b in blocks() if owner(b) == "catalog-streaming"]
    assert catalog, "no se encontró ningún location de catálogo"
    for pattern, body in catalog:
        assert effective("proxy_next_upstream", body) == "error timeout http_502 http_503", pattern
        assert effective("proxy_next_upstream_tries", body) == "2", pattern
        assert effective("proxy_connect_timeout", body) == "1s", pattern
        assert "non_idempotent" not in (effective("proxy_next_upstream", body) or ""), f"{pattern}: sin non_idempotent, POST/PATCH no se repiten"
