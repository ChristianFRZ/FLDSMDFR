import ast
import dataclasses
import itertools
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import respx
from sqlalchemy import func, select

import seed
from app.core.db import session_scope
from app.core.security import create_access_token
from app.modules.analytics.latency import flush_latency
from app.modules.analytics.models import PlaysHourly
from app.modules.catalog import import_jobs
from app.modules.catalog.models import Artist, Song
from app.modules.playback.models import Playback
from app.modules.playlists.models import Playlist
from app.modules.social.models import Favorite, Follow, Tape, TapeTrack
from app.modules.users.models import User
from seed import audio
from tests.media import mp3

API = "https://api.jamendo.com/v3.0/tracks/"
BACKEND = Path(__file__).resolve().parents[2]
SIZES = seed.Sizes(
    listeners=6, composers=2, admins=1, tracks_per_composer=3, plays=300, days=14,
    tapes=3, playlists=3, genres=("rock", "pop"), per_genre=4,
)
ids = itertools.count(1000)


def page(request):
    if int(request.url.params.get("offset", 0)) > 0:
        return httpx.Response(200, json={"headers": {"status": "success"}, "results": []})
    results = []
    for _ in range(4):
        i = next(ids)
        results.append({
            "id": str(i), "name": f"Pista {i}", "duration": 120, "artist_id": str(i % 3), "artist_name": f"Artista {i % 3}",
            "album_name": "Disco", "album_id": str(i % 3), "license_ccurl": "http://creativecommons.org/licenses/by/3.0/",
            "image": "https://img.example/x.jpg", "audio": f"https://audio.example/{i}", "shareurl": f"https://jamendo.com/{i}",
            "musicinfo": {"tags": {"genres": ["rock"], "vartags": []}},
        })
    return httpx.Response(200, json={"headers": {"status": "success"}, "results": results})


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch):
    """ffmpeg solo existe en la imagen de Docker; el resto del camino es real."""

    async def instant(_):
        return None

    def render(path, _frequency, _seconds):
        path.write_bytes(mp3(100))

    monkeypatch.setattr(audio, "_render", render)
    monkeypatch.setattr(import_jobs, "_sleep", instant)
    monkeypatch.setenv("DEMO_PASSWORD", "una-clave-de-demo")


@pytest.fixture
def jamendo():
    with respx.mock(assert_all_called=False) as mock:
        yield mock.get(API).mock(side_effect=page)


async def count(model, *where):
    async with session_scope() as session:
        return await session.scalar(select(func.count()).select_from(model).where(*where))


async def totals():
    tables = (User, Artist, Song, Playback, Tape, TapeTrack, Playlist, Favorite, Follow)
    plays = 0
    async with session_scope() as session:
        plays = await session.scalar(select(func.coalesce(func.sum(PlaysHourly.plays), 0)))
    return [await count(table) for table in tables] + [plays]


async def test_seed_idempotent(jamendo):
    await seed.run_all(SIZES)
    first, calls = await totals(), jamendo.call_count
    assert first[3] > 0
    await seed.run_all(SIZES)
    assert await totals() == first
    assert jamendo.call_count == calls  # La segunda corrida no gasta cuota de Jamendo.


async def test_simulated_rows_marked_is_demo(jamendo):
    await seed.run_all(SIZES)
    assert await count(User, User.is_demo.is_(False)) == 0
    assert await count(Playback, Playback.is_demo.is_(False)) == 0
    assert await count(Tape, Tape.is_demo.is_(False)) == 0
    assert await count(Playlist, Playlist.is_demo.is_(False)) == 0
    assert await count(Song, Song.source == "local", Song.is_demo.is_(False)) == 0
    assert await count(Song, Song.source == "jamendo", Song.is_demo.is_(True)) == 0


async def test_clear_removes_only_demo(jamendo, client, listener, make_song):
    real_song = await make_song()
    await client.post(
        "/api/playbacks",
        json={"playback_id": str(uuid4()), "song_id": str(real_song.id), "listened_seconds": 30},
        headers=listener.headers,
    )
    await seed.run_all(SIZES)
    jamendo_songs = await count(Song, Song.source == "jamendo")
    assert jamendo_songs > 0

    await seed.clear()

    assert await count(User, User.is_demo.is_(True)) == 0
    assert await count(User, User.id == listener.id) == 1
    assert await count(Song, Song.is_demo.is_(True)) == 0
    assert await count(Song, Song.id == real_song.id) == 1
    assert await count(Song, Song.source == "jamendo") == jamendo_songs
    assert await count(Playback) == 1
    assert await count(Tape) == 0
    async with session_scope() as session:
        assert await session.scalar(select(func.sum(PlaysHourly.plays))) == 1


async def demo_user(role):
    async with session_scope() as session:
        user = (await session.execute(select(User).where(User.role == role, User.is_demo.is_(True)))).scalars().first()
    return {"authorization": f"Bearer {create_access_token(user.id, role)}"}


CHARTS = [
    ("admin", "/api/metrics/plays?scope=global&group=day&days=30"),
    ("composer", "/api/metrics/plays?scope=composer&group=day&days=30"),
    ("admin", "/api/metrics/top?scope=global&kind=songs"),
    ("listener", "/api/metrics/top?scope=me&kind=songs"),
    ("admin", "/api/metrics/genres?scope=global"),
    ("listener", "/api/metrics/genres?scope=me"),
    ("admin", "/api/metrics/heatmap?days=30"),
    ("admin", "/api/metrics/catalog-sources"),
    ("admin", "/api/metrics/user-growth?days=30"),
    ("composer", "/api/metrics/retention"),
]


@pytest.mark.parametrize(("role", "url"), CHARTS)
async def test_all_chart_routes_have_data_after_seed(jamendo, client, role, url):
    await seed.run_all(SIZES)
    r = await client.get(url, headers=await demo_user(role))
    assert r.status_code == 200
    assert r.json()["items"]


@pytest.mark.parametrize(
    ("url", "field"),
    [
        ("/api/metrics/tape-activity", "dedications"),
        ("/api/metrics/releases?scope=global", "scheduled"),
        ("/api/metrics/duplicates", "duplicates_discarded"),
    ],
)
async def test_counter_charts_have_data_after_seed(jamendo, client, url, field):
    await seed.run_all(SIZES)
    r = await client.get(url, headers=await demo_user("admin"))
    assert r.json()[field] > 0


async def test_composer_counts_have_data_after_seed(jamendo, client):
    await seed.run_all(SIZES)
    r = await client.get("/api/metrics/inclusions", headers=await demo_user("composer"))
    assert r.status_code == 200
    assert r.json()["playlists"] + r.json()["tapes"] > 0


async def test_latency_chart_measures_real_requests(jamendo, client):
    """No se simula: la latencia sale de peticiones de verdad, también durante la demo."""
    await seed.run_all(SIZES)
    headers = await demo_user("admin")
    await client.get("/api/songs", headers=headers)
    await flush_latency(include_current=True)
    r = await client.get("/api/metrics/latency?minutes=5", headers=headers)
    assert r.json()["items"]


async def test_local_tracks_are_playable(jamendo, client):
    await seed.run_all(SIZES)
    async with session_scope() as session:
        song = await session.scalar(select(Song.id).where(Song.source == "local", Song.status == "published").limit(1))
    headers = await demo_user("listener")
    ticket = (await client.post(f"/api/songs/{song}/stream-ticket", headers=headers)).json()["ticket"]
    r = await client.get(f"/api/songs/{song}/stream?ticket={ticket}", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206


async def test_demo_login_uses_the_configured_password(jamendo, client):
    await seed.run_all(SIZES)
    async with session_scope() as session:
        email = await session.scalar(select(User.email).where(User.is_demo.is_(True)).limit(1))
    r = await client.post("/api/auth/login", json={"email": email, "password": "una-clave-de-demo"})
    assert r.status_code == 200


def test_without_configured_password_each_run_gets_a_random_one(monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD")
    assert len(seed.demo_password()) >= 16
    assert seed.demo_password() != seed.demo_password()


def test_startup_does_not_run_seed():
    for path in (BACKEND / "app").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            names += [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            assert not any(name.split(".")[0] == "seed" for name in names), path
    assert "seed" not in (BACKEND.parent / "Dockerfile").read_text().split("CMD")[-1]


def test_seed_only_uses_public_interfaces():
    for path in (BACKEND / "seed").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app.modules."):
                assert node.module.endswith(".public"), f"{path.name}: {node.module}"


async def test_new_genres_import_again(jamendo):
    await seed.run_all(SIZES)
    calls = jamendo.call_count
    await seed.run_all(dataclasses.replace(SIZES, genres=("jazz",)))
    assert jamendo.call_count > calls


async def test_partial_import_runs_again(jamendo):
    """Si una importación quedó corta, repetir la semilla la completa."""
    await seed.run_all(SIZES)
    calls = jamendo.call_count
    await seed.run_all(dataclasses.replace(SIZES, per_genre=100))
    assert jamendo.call_count > calls
