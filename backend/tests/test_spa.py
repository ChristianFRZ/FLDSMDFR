import httpx
import pytest

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
async def spa(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html><title>MELOXO</title>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path.parent / "secreto.txt").write_text("no")
    monkeypatch.setattr(get_settings(), "STATIC_DIR", str(tmp_path))
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_spa_fallback(spa):
    r = await spa.get("/casetes/123")
    assert r.status_code == 200
    assert "MELOXO" in r.text


async def test_root_serves_index(spa):
    assert "MELOXO" in (await spa.get("/")).text


async def test_static_file_served(spa):
    r = await spa.get("/assets/app.js")
    assert r.text == "console.log(1)"


async def test_missing_asset_is_404(spa):
    assert (await spa.get("/assets/nada.js")).status_code == 404


async def test_api_404_not_spa(spa):
    r = await spa.get("/api/nada")
    assert r.status_code == 404
    assert r.json()["error"]["code"]


async def test_no_path_traversal(spa):
    r = await spa.get("/..%2Fsecreto.txt")
    assert "no" != r.text


async def test_without_static_dir_root_is_404(client):
    assert (await client.get("/")).status_code == 404
