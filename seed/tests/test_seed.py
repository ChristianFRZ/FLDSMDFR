import dataclasses
import json
import uuid
from datetime import datetime

import httpx
import pytest
import respx

import seed
from seed import audio, internal

USERS = "http://users.test:8001"
CATALOG = "http://catalog.test:8002"
PLAYBACK = "http://playback.test:8003"
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 413  # MPEG1 Layer III, 128 kbps, 44.1 kHz
SIZES = seed.Sizes(
    listeners=6, composers=2, admins=1, tracks_per_composer=3, plays=300, days=14,
    tapes=3, playlists=3, genres=("rock", "pop"), per_genre=4,
)
SONGS = [
    {"id": str(uuid.uuid4()), "artist_id": str(uuid.uuid4()), "duration": 120.0, "source": "local" if i % 2 else "jamendo"}
    for i in range(20)
]


@pytest.fixture(autouse=True)
def environment(monkeypatch, tmp_path):
    """ffmpeg solo existe en la imagen de Docker; aquí los tonos son un MP3 mínimo."""
    monkeypatch.setenv("USERS_URL", USERS)
    monkeypatch.setenv("CATALOG_URL", CATALOG)
    monkeypatch.setenv("PLAYBACK_URL", PLAYBACK)
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    monkeypatch.setenv("DEMO_PASSWORD", "una-clave-de-demo")
    monkeypatch.setattr(audio, "_render", lambda path, _frequency, _seconds: path.write_bytes(MP3_FRAME * 100))


class Services:
    """Los tres servicios simulados: guarda cada petición en orden."""

    def __init__(self, mock: respx.MockRouter):
        self.import_done = False
        self.import_status = "done"
        self.mock = mock
        mock.post(f"{USERS}/internal/demo/users").mock(side_effect=self.insert_users)
        mock.get(f"{USERS}/internal/demo/users/ids").respond(json={"ids": [str(uuid.uuid4())]})
        mock.get(f"{CATALOG}/internal/demo/catalog/import-done").mock(side_effect=lambda _: httpx.Response(200, json={"done": self.import_done}))
        mock.post(f"{CATALOG}/internal/demo/catalog/import").mock(side_effect=self.run_import)
        mock.get(f"{CATALOG}/internal/demo/catalog/listenable").respond(json=SONGS)
        for url in (
            f"{USERS}/internal/demo/users/clear", f"{USERS}/internal/demo/playlists", f"{USERS}/internal/demo/playlists/clear",
            f"{USERS}/internal/demo/social", f"{USERS}/internal/demo/social/clear",
            f"{CATALOG}/internal/demo/catalog", f"{CATALOG}/internal/demo/catalog/clear",
            f"{PLAYBACK}/internal/demo/playbacks", f"{PLAYBACK}/internal/demo/playbacks/clear",
            f"{PLAYBACK}/internal/demo/aggregates/rebuild", f"{PLAYBACK}/internal/demo/aggregates/catch-up",
        ):
            mock.post(url).respond(204)

    def insert_users(self, request):
        body = json.loads(request.content)
        return httpx.Response(200, json={"ids": {u["email"]: str(uuid.uuid4()) for u in body["users"]}})

    def run_import(self, request):
        self.import_done = True
        return httpx.Response(200, json={"status": self.import_status, "imported": 7, "error": "sin cuota"})

    def calls(self) -> list[tuple[str, str]]:
        return [(c.request.method, c.request.url.path.removeprefix("/internal/demo")) for c in self.mock.calls]

    def bodies(self, path: str) -> list[dict]:
        return [json.loads(c.request.content) for c in self.mock.calls if c.request.url.path == f"/internal/demo{path}" and c.request.content]


@pytest.fixture
def services():
    with respx.mock(assert_all_called=False) as mock:
        yield Services(mock)


async def test_seed_all_calls_users_then_catalog_then_playback_demo_routes(services):
    await seed.run_all(SIZES)
    posts = [path for method, path in services.calls() if method == "POST" and path != "/catalog/import"]
    first = {path: posts.index(path) for path in ("/users", "/catalog", "/playlists", "/social", "/playbacks", "/aggregates/catch-up")}
    assert list(first) == sorted(first, key=first.get)
    assert services.calls()[0] == ("GET", "/catalog/import-done")  # La importación de Jamendo va antes que todo lo simulado.
    assert posts.index("/users") > posts.index("/aggregates/rebuild")  # Empieza de cero.

    users = services.bodies("/users")[0]
    assert users["password"] == "una-clave-de-demo"
    assert [u["role"] for u in users["users"]].count("listener") == 6
    assert users["users"][0]["email"] == "oyente00@demo.meloxo.dev"
    datetime.fromisoformat(users["users"][0]["created_at"])
    composers = services.bodies("/catalog")[0]["composers"]
    assert len(composers) == 2 and len(composers[0]["tracks"]) == 3
    assert composers[0]["tracks"][-1]["status"] == "scheduled"
    assert composers[0]["tracks"][0]["audio_path"].startswith("demo/tono-")
    assert len(services.bodies("/playlists")[0]["playlists"]) == 3
    social = services.bodies("/social")[0]
    assert len(social["tapes"]) == 3 and social["favorites"] and social["follows"]
    playbacks = services.bodies("/playbacks")[0]
    assert len(playbacks["plays"]) == 300 and playbacks["duplicates"] == 3


async def test_seed_clear_calls_every_clear_route(services):
    await seed.clear()
    assert services.calls() == [
        ("GET", "/users/ids"),
        ("POST", "/social/clear"),
        ("POST", "/playlists/clear"),
        ("POST", "/playbacks/clear"),
        ("POST", "/catalog/clear"),
        ("POST", "/users/clear"),
        ("POST", "/aggregates/rebuild"),
    ]
    assert len(services.bodies("/social/clear")[0]["user_ids"]) == 1


async def test_clear_removes_the_generated_tones(services, tmp_path):
    await audio.ensure_tones(2)
    assert (tmp_path / "demo" / "tono-00.mp3").exists()
    await seed.clear()
    assert not (tmp_path / "demo").exists()


async def test_second_all_does_not_ask_jamendo_again(services):
    await seed.run_all(SIZES)
    await seed.run_all(SIZES)
    assert len(services.bodies("/catalog/import")) == 1
    assert len([1 for c in services.calls() if c == ("POST", "/users")]) == 2


async def test_import_sends_genres_and_minimum_threshold(services):
    message = await seed.import_catalog(SIZES)
    assert message == "Catálogo de Jamendo: 7 pistas importadas."
    assert services.bodies("/catalog/import") == [{"genres": ["rock", "pop"], "per_genre": 4}]
    query = dict(services.mock.calls[0].request.url.params)
    assert query == {"genres": "rock,pop", "minimum": "7"}


async def test_already_imported_catalog_makes_no_import_request(services):
    services.import_done = True
    assert "ya importado" in await seed.import_catalog(SIZES)
    assert services.bodies("/catalog/import") == []


async def test_stopped_import_raises_with_the_reason(services):
    services.import_status = "failed"
    with pytest.raises(RuntimeError, match="7 pistas: sin cuota"):
        await seed.import_catalog(SIZES)


async def test_same_random_seed_sends_the_same_bodies(services):
    async def bodies():
        await seed.run_activity(SIZES)
        playbacks = services.bodies("/playbacks")[-1]["plays"]
        # Las horas dependen del reloj; la elección de pistas y de tiempo escuchado, no.
        return [p["listened_seconds"] for p in playbacks]

    first = await bodies()
    assert await bodies() == first


async def test_activity_fails_when_the_catalog_has_no_songs(services):
    services.mock.get(f"{CATALOG}/internal/demo/catalog/listenable").respond(json=[])
    with pytest.raises(RuntimeError, match="catálogo"):
        await seed.run_activity(SIZES)


async def test_service_error_shows_the_api_code_and_message(services):
    services.mock.post(f"{CATALOG}/internal/demo/catalog").respond(
        422, json={"error": {"code": "validation_error", "message": "Datos no válidos", "detail": None}}
    )
    with pytest.raises(internal.SeedError, match=r"catalog-streaming.*422.*validation_error.*Datos no válidos"):
        await seed.run_activity(SIZES)


async def test_unreachable_service_gives_a_clear_error(services):
    services.mock.get(f"{USERS}/internal/demo/users/ids").mock(side_effect=httpx.ConnectError("sin ruta"))
    with pytest.raises(internal.SeedError, match="users-playlists.*no responde"):
        await seed.clear()


def test_clients_use_urls_from_the_environment(monkeypatch):
    assert internal.users().base_url == USERS
    assert internal.catalog().base_url == CATALOG
    assert internal.playback().base_url == PLAYBACK
    for name in ("USERS_URL", "CATALOG_URL", "PLAYBACK_URL"):
        monkeypatch.delenv(name)
    assert internal.users().base_url == "http://users-playlists:8001"
    assert internal.catalog().base_url == "http://catalog-streaming:8002"
    assert internal.playback().base_url == "http://playback-metrics:8003"


def test_requests_do_not_use_the_short_service_timeout():
    assert internal.TIMEOUT.read >= 300


def test_without_configured_password_each_run_gets_a_random_one(monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD")
    assert len(seed.demo_password()) >= 16
    assert seed.demo_password() != seed.demo_password()


async def test_report_shows_accounts_and_the_password(services, capsys):
    from seed import __main__ as cli

    await cli.main("activity", SIZES)
    out = capsys.readouterr().out
    assert "Simulado: 300 reproducciones, 3 casetes, 3 playlists." in out
    assert "oyente00@demo.meloxo.dev" in out
    assert "Contraseña de las cuentas ficticias: una-clave-de-demo" in out


async def test_cli_catalog_and_clear_messages(services, capsys):
    from seed import __main__ as cli

    await cli.main("catalog", SIZES)
    await cli.main("clear", SIZES)
    out = capsys.readouterr().out
    assert "Catálogo de Jamendo: 7 pistas importadas." in out
    assert "Datos simulados borrados." in out


async def test_cli_users_only_creates_accounts(services):
    from seed import __main__ as cli

    await cli.main("users", SIZES)
    posts = {path for method, path in services.calls() if method == "POST"}
    assert "/users" in posts and not posts & {"/catalog", "/social", "/playbacks"}


def test_sizes_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        SIZES.plays = 1  # type: ignore[misc]
