from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from app.config import get_settings
from app.main import create_app

INDEX_HTML = '<!doctype html><html><body><div id="app"></div></body></html>'


def _build_dist(root: Path) -> Path:
    dist = root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('fldsmdfr')", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    # Archivo fuera de dist: nunca debe poder servirse.
    (root / "secreto.txt").write_text("no", encoding="utf-8")
    return dist


@pytest.fixture
def spa_app(tmp_path, monkeypatch) -> FastAPI:
    dist = _build_dist(tmp_path)
    monkeypatch.setenv("FLDSMDFR_UI_DIST_DIR", str(dist))
    get_settings.cache_clear()
    try:
        yield create_app()
    finally:
        get_settings.cache_clear()


@pytest_asyncio.fixture
async def spa_client(spa_app):
    transport = httpx.ASGITransport(app=spa_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.parametrize("path", ["/", "/cabina", "/acceso", "/una/ruta/profunda"])
async def test_spa_routes_return_index(spa_client, path):
    response = await spa_client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="app"' in response.text


async def test_index_is_not_cached(spa_client):
    response = await spa_client.get("/cabina")
    assert response.headers["cache-control"] == "no-cache"


async def test_assets_are_served(spa_client):
    response = await spa_client.get("/assets/app.js")
    assert response.status_code == 200
    assert "fldsmdfr" in response.text


async def test_root_files_in_dist_are_served(spa_client):
    response = await spa_client.get("/favicon.svg")
    assert response.status_code == 200
    assert response.text == "<svg/>"


async def test_missing_asset_is_404_not_index(spa_client):
    response = await spa_client.get("/assets/no-existe.js")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def _assert_index(response):
    assert response.status_code == 200
    assert 'id="app"' in response.text


async def test_relative_traversal_falls_back_to_index(spa_client):
    _assert_index(await spa_client.get("/..%2Fsecreto.txt"))


async def test_absolute_path_outside_dist_falls_back_to_index(spa_client, tmp_path):
    # "%2F" se decodifica: full_path = "/<tmp>/secreto.txt"; root / ruta_absoluta = ruta_absoluta,
    # el archivo existe, y solo el control is_relative_to impide servirlo.
    secret = tmp_path / "secreto.txt"
    assert secret.is_file()
    _assert_index(await spa_client.get("/" + str(secret).replace("/", "%2F")))


@pytest.mark.parametrize("path", ["/%00", "/x%00y", "/assets%00.js"])
async def test_null_byte_falls_back_to_index(spa_client, path):
    _assert_index(await spa_client.get(path))


@pytest.mark.parametrize("path", ["/api/nada", "/api", "/docs/nada"])
async def test_api_and_docs_unknown_paths_stay_json_404(spa_client, path):
    response = await spa_client.get(path)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "No encontramos lo que buscas."}
    }


async def test_spa_does_not_shadow_docs_or_api(spa_client):
    assert (await spa_client.get("/docs")).status_code == 200
    assert (await spa_client.get("/openapi.json")).json()["info"]["title"] == "FLDSMDFR"
    response = await spa_client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_without_build_the_spa_is_not_mounted(tmp_path, monkeypatch):
    monkeypatch.setenv("FLDSMDFR_UI_DIST_DIR", str(tmp_path / "sin-build"))
    get_settings.cache_clear()
    try:
        bare = create_app()
    finally:
        get_settings.cache_clear()
    transport = httpx.ASGITransport(app=bare)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_unknown_api_route_with_other_methods_stays_404(spa_client):
    response = await spa_client.post("/api/nada", json={})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
