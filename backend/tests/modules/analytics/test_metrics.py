import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import respx

from app.core.config import get_settings
from app.core.db import session_scope
from app.modules.analytics import latency
from app.modules.analytics.aggregates import refresh_aggregates
from app.modules.playback.models import Playback


async def post_play(client, user, song, seconds=12):
    r = await client.post(
        "/api/playbacks",
        json={"playback_id": str(uuid4()), "song_id": str(song.id), "listened_seconds": seconds},
        headers=user.headers,
    )
    assert r.status_code == 201, r.text


async def refresh():
    return await refresh_aggregates(settle_seconds=0)


async def get(client, user, name, **params):
    r = await client.get(f"/api/metrics/{name}", params=params, headers=user.headers)
    assert r.status_code == 200, r.text
    return r.json()


async def test_event_reflected_after_refresh(client, admin, listener, make_song):
    song = await make_song()
    await post_play(client, listener, song)
    assert await refresh() == 1
    item = (await get(client, admin, "top"))["items"][0]
    assert item["plays"] == 1
    assert item["label"] == "Luz de carretera"


async def test_fresh_events_wait_to_settle(client, listener, make_song):
    """Un seq menor puede confirmarse después que uno mayor: el cursor no debe saltárselo."""
    await post_play(client, listener, await make_song())
    assert await refresh_aggregates(settle_seconds=60) == 0
    assert await refresh() == 1


async def test_refresh_does_not_reprocess(client, listener, make_song):
    await post_play(client, listener, await make_song())
    await refresh()
    assert await refresh() == 0


async def test_two_workers_do_not_double_count(client, admin, listener, make_song):
    song = await make_song()
    for _ in range(5):
        await post_play(client, listener, song)
    await asyncio.gather(refresh(), refresh(), refresh())
    await refresh()
    assert (await get(client, admin, "top"))["items"][0]["plays"] == 5


async def test_multi_genre_song_counts_once(client, admin, listener, make_song):
    song = await make_song(genres=("rock", "pop"))
    await post_play(client, listener, song)
    await refresh()
    assert (await get(client, admin, "top"))["items"][0]["plays"] == 1
    assert (await get(client, admin, "genres"))["items"] == [{"genre": "rock", "plays": 1}]


async def test_song_without_genre(client, admin, listener, make_song):
    await post_play(client, listener, await make_song(genres=()))
    await refresh()
    assert (await get(client, admin, "genres"))["items"][0]["genre"] == "sin género"


async def test_top_artists(client, admin, listener, make_song):
    await post_play(client, listener, await make_song(artist="Marea"))
    await refresh()
    assert (await get(client, admin, "top", kind="artists"))["items"][0]["label"] == "Marea"


async def test_listener_scope_me_is_own_data(client, listener, make_user, make_song):
    other, mine, theirs = await make_user(), await make_song(title="Mía"), await make_song(title="Ajena")
    await post_play(client, listener, mine)
    await post_play(client, other, theirs)
    await refresh()
    assert [i["label"] for i in (await get(client, listener, "top", scope="me"))["items"]] == ["Mía"]
    assert (await get(client, listener, "genres", scope="me"))["items"][0]["plays"] == 1


async def test_composer_sees_only_own_songs(client, listener, composer, make_song):
    mine = await make_song(title="Mía", artist="Yo", owner=composer.id)
    await post_play(client, listener, mine)
    await post_play(client, listener, await make_song(title="Ajena", artist="Otro"))
    await refresh()
    items = (await get(client, composer, "plays", scope="composer"))["items"]
    assert sum(i["plays"] for i in items) == 1


async def test_composer_data_is_anonymous(client, listener, composer, make_song):
    song = await make_song(artist="Yo", owner=composer.id, duration=20)
    await post_play(client, listener, song)
    await refresh()
    for name, params in (("plays", {"scope": "composer"}), ("retention", {}), ("inclusions", {}), ("releases", {"scope": "composer"})):
        r = await client.get(f"/api/metrics/{name}", params=params, headers=composer.headers)
        assert listener.id not in r.text
        assert listener.email not in r.text


async def test_retention_per_track(client, listener, composer, make_song):
    song = await make_song(artist="Yo", owner=composer.id, duration=100)
    await post_play(client, listener, song, seconds=60)
    await post_play(client, listener, song, seconds=10)
    item = (await get(client, composer, "retention"))["items"][0]
    assert (item["title"], item["at_10s"], item["at_50"], item["at_100"]) == ("Luz de carretera", 2, 1, 0)


async def test_inclusions_are_counts(client, listener, composer, make_song):
    song = await make_song(artist="Yo", owner=composer.id)
    playlist = (await client.post("/api/playlists", json={"name": "x"}, headers=listener.headers)).json()
    await client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=listener.headers)
    tape = (await client.post("/api/tapes", json={"title": "x"}, headers=listener.headers)).json()
    await client.post(f"/api/tapes/{tape['id']}/tracks", json={"song_id": str(song.id)}, headers=listener.headers)
    assert await get(client, composer, "inclusions") == {"playlists": 1, "tapes": 1}


async def test_heatmap_uses_requested_timezone(client, admin, listener, make_song):
    await post_play(client, listener, await make_song())
    await refresh()
    utc = (await get(client, admin, "heatmap", tz="UTC"))["items"][0]
    lima = (await get(client, admin, "heatmap", tz="America/Lima"))["items"][0]
    assert (utc["hour"] - lima["hour"]) % 24 == 5


async def test_unknown_timezone_422(client, admin):
    r = await client.get("/api/metrics/heatmap", params={"tz": "Marte/Base"}, headers=admin.headers)
    assert r.status_code == 422


async def test_plays_by_day_and_hour(client, admin, listener, make_song):
    await post_play(client, listener, await make_song())
    await refresh()
    assert len((await get(client, admin, "plays", group="day"))["items"]) == 1
    assert (await get(client, admin, "plays", group="hour"))["items"][0]["plays"] == 1


@pytest.mark.parametrize(
    "name,params",
    [
        ("top", {}),
        ("genres", {}),
        ("plays", {}),
        ("heatmap", {}),
        ("catalog-sources", {}),
        ("user-growth", {}),
        ("tape-activity", {}),
        ("latency", {}),
        ("duplicates", {}),
        ("releases", {}),
    ],
)
async def test_listener_cannot_get_global(client, listener, name, params):
    r = await client.get(f"/api/metrics/{name}", params=params, headers=listener.headers)
    assert r.status_code == 403


@pytest.mark.parametrize("name", ["retention", "inclusions"])
async def test_listener_cannot_get_composer_only(client, listener, name):
    assert (await client.get(f"/api/metrics/{name}", headers=listener.headers)).status_code == 403


async def test_listener_cannot_use_composer_scope(client, listener):
    r = await client.get("/api/metrics/plays", params={"scope": "composer"}, headers=listener.headers)
    assert r.status_code == 403


async def test_composer_cannot_get_global(client, composer):
    assert (await client.get("/api/metrics/plays", headers=composer.headers)).status_code == 403


async def test_metrics_need_session(client):
    assert (await client.get("/api/metrics/top")).status_code == 401


@pytest.mark.parametrize(
    "name,role,params",
    [
        ("top", "admin", {}),
        ("top", "listener", {"scope": "me"}),
        ("plays", "admin", {}),
        ("plays", "composer", {"scope": "composer"}),
        ("genres", "admin", {}),
        ("genres", "listener", {"scope": "me"}),
        ("heatmap", "admin", {}),
        ("catalog-sources", "admin", {}),
        ("user-growth", "admin", {}),
        ("retention", "composer", {}),
        ("tape-activity", "admin", {}),
        ("releases", "admin", {}),
        ("releases", "composer", {"scope": "composer"}),
        ("latency", "admin", {}),
        ("duplicates", "admin", {}),
        ("inclusions", "composer", {}),
    ],
)
async def test_each_route_ok_on_empty_data(client, make_user, name, role, params):
    user = await make_user(role=role)
    await get(client, user, name, **params)


async def test_user_growth_counts_roles(client, admin):
    items = (await get(client, admin, "user-growth"))["items"]
    assert items[-1]["admin"] >= 1


async def test_duplicates_counter(client, admin, listener, make_song):
    song, pid = await make_song(), str(uuid4())
    body = {"playback_id": pid, "song_id": str(song.id), "listened_seconds": 12}
    for _ in range(3):
        await client.post("/api/playbacks", json=body, headers=listener.headers)
    assert (await get(client, admin, "duplicates"))["duplicates_discarded"] == 2


async def test_catalog_sources(client, admin, make_song):
    await make_song(source="jamendo", artist="R")
    await make_song(source="local", artist="L")
    items = (await get(client, admin, "catalog-sources"))["items"]
    assert {i["source"]: i["count"] for i in items} == {"jamendo": 1, "local": 1}


async def test_latency_grouped_by_module(client, admin, listener):
    latency.buffer.clear()
    await client.get("/api/songs", headers=listener.headers)
    await client.get("/api/playlists", headers=listener.headers)
    await client.get("/api/playlists/no-es-uuid", headers=listener.headers)
    await latency.flush_latency(include_current=True)
    items = (await get(client, admin, "latency"))["items"]
    modules = {i["module"]: i for i in items}
    assert modules["catalog"]["count"] == 1
    assert modules["playlists"]["count"] == 2
    assert modules["playlists"]["errors"] == 0
    assert modules["catalog"]["p95_ms"] >= modules["catalog"]["p50_ms"] >= 0


async def test_latency_counts_server_errors(client, admin, listener, monkeypatch):
    from app.modules.playlists import service

    latency.buffer.clear()

    async def broken(*_):
        raise RuntimeError("falla")

    monkeypatch.setattr(service, "list_mine", broken)
    assert (await client.get("/api/playlists", headers=listener.headers)).status_code == 500
    await latency.flush_latency(include_current=True)
    modules = {i["module"]: i for i in (await get(client, admin, "latency"))["items"]}
    assert modules["playlists"]["errors"] == 1


async def test_flush_keeps_current_minute_by_default():
    latency.buffer.clear()
    latency.record("catalog", 10, False)
    await latency.flush_latency()
    assert latency.buffer


async def test_flush_merges_same_minute(client, admin):
    latency.buffer.clear()
    latency.record("catalog", 10, False)
    await latency.flush_latency(include_current=True)
    latency.record("catalog", 30, True)
    await latency.flush_latency(include_current=True)
    item = next(i for i in (await get(client, admin, "latency"))["items"] if i["module"] == "catalog")
    assert (item["count"], item["errors"]) == (2, 1)
    assert item["p50_ms"] == 20


@pytest.mark.parametrize(
    "path,module",
    [
        ("/api/songs/1/stream", "streaming"),
        ("/api/songs", "catalog"),
        ("/api/composer/tracks", "catalog"),
        ("/api/admin/songs", "catalog"),
        ("/api/admin/users", "users"),
        ("/api/auth/login", "users"),
        ("/api/tapes/1", "social"),
        ("/api/playbacks", "playback"),
        ("/api/metrics/top", "analytics"),
        ("/api/admin/health", "analytics"),
        ("/assets/app.js", None),
    ],
)
def test_module_for_path(path, module):
    assert latency.module_for(path) == module


@respx.mock
async def test_health_reports_db_and_jamendo(client, admin):
    url = f"{get_settings().JAMENDO_API_URL}/tracks/"
    respx.get(url).mock(return_value=httpx.Response(200, json={"headers": {"status": "success"}, "results": []}))
    r = await client.get("/api/admin/health", headers=admin.headers)
    states = {s["name"]: s["status"] for s in r.json()["services"]}
    assert states == {"app": "up", "database": "up", "jamendo": "up", "aggregates": "up"}


@respx.mock
async def test_health_with_jamendo_down_is_200(client, admin):
    respx.get(f"{get_settings().JAMENDO_API_URL}/tracks/").mock(side_effect=httpx.ConnectError("caído"))
    r = await client.get("/api/admin/health", headers=admin.headers)
    assert r.status_code == 200
    states = {s["name"]: s["status"] for s in r.json()["services"]}
    assert (states["app"], states["jamendo"]) == ("up", "down")


@respx.mock
async def test_health_gives_detail_per_service(client, admin):
    respx.get(f"{get_settings().JAMENDO_API_URL}/tracks/").mock(
        return_value=httpx.Response(200, json={"headers": {"status": "success"}, "results": []})
    )
    r = await client.get("/api/admin/health", headers=admin.headers)
    services = {s["name"]: s for s in r.json()["services"]}
    assert services["app"]["uptime_seconds"] >= 0
    assert services["database"]["ms"] >= 0


async def test_health_needs_admin(client, listener):
    assert (await client.get("/api/admin/health", headers=listener.headers)).status_code == 403


async def test_health_system_reports_resources_and_versions(client, admin):
    body = (await client.get("/api/admin/health/system", headers=admin.headers)).json()
    assert 0 < body["disk"]["used_bytes"] <= body["disk"]["total_bytes"]
    assert body["database"]["size_bytes"] > 0
    assert 0 < body["database"]["connections"] <= body["database"]["max_connections"]
    assert body["system"]["version"] == get_settings().APP_VERSION
    assert body["system"]["postgres"].split(".")[0].isdigit()
    assert body["system"]["python"].startswith("3.")
    assert body["system"]["started_at"]


async def test_health_activity_counts_recent_real_plays(client, admin, listener, make_user, make_song):
    other, song = await make_user(), await make_song()
    now = datetime.now(UTC)
    async with session_scope() as session:
        session.add_all(
            [
                Playback(playback_id=uuid4(), user_id=listener.id, song_id=song.id, listened_seconds=30, started_at=now),
                Playback(playback_id=uuid4(), user_id=listener.id, song_id=song.id, listened_seconds=30, started_at=now),
                Playback(playback_id=uuid4(), user_id=other.id, song_id=song.id, listened_seconds=30, started_at=now - timedelta(hours=2)),
                Playback(playback_id=uuid4(), user_id=other.id, song_id=song.id, listened_seconds=30, started_at=now, is_demo=True),
            ]
        )
    body = (await client.get("/api/admin/health/activity", headers=admin.headers)).json()
    assert body == {"minutes": 30, "listeners": 1, "plays": 2}


@pytest.mark.parametrize("path", ["/api/admin/health/system", "/api/admin/health/activity"])
async def test_health_details_need_admin(client, listener, path):
    assert (await client.get(path, headers=listener.headers)).status_code == 403


async def test_csv_export(client, admin, listener, make_song):
    await post_play(client, listener, await make_song())
    await refresh()
    r = await client.get("/api/admin/reports/top.csv", headers=admin.headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].split(",")[1:] == ["label", "plays"]
    assert "Luz de carretera" in lines[1]


async def test_csv_export_by_hour(client, admin, listener, make_song):
    await post_play(client, listener, await make_song())
    await refresh()
    r = await client.get("/api/admin/reports/plays-hourly.csv?days=2", headers=admin.headers)
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0] == "bucket,plays"
    assert lines[1].endswith(":00:00,1")


async def test_csv_neutralizes_formulas(client, admin, listener, make_song):
    await post_play(client, listener, await make_song(title='=HYPERLINK("http://x")'))
    await refresh()
    r = await client.get("/api/admin/reports/top.csv", headers=admin.headers)
    assert "'=HYPERLINK" in r.text


async def test_csv_unknown_report_404(client, admin):
    assert (await client.get("/api/admin/reports/nada.csv", headers=admin.headers)).status_code == 404


async def test_csv_needs_admin(client, listener):
    assert (await client.get("/api/admin/reports/top.csv", headers=listener.headers)).status_code == 403


async def test_top_respects_days_window(client, admin, listener, make_song):
    from app.core.db import session_scope
    from app.modules.analytics.models import PlaysHourly

    song = await make_song()
    async with session_scope() as session:
        session.add(
            PlaysHourly(
                hour=datetime.now(UTC) - timedelta(days=40),
                song_id=song.id,
                artist_id=song.artist_id,
                genre="rock",
                plays=7,
            )
        )
    assert (await get(client, admin, "top", days=30))["items"] == []
    assert (await get(client, admin, "top", days=60))["items"][0]["plays"] == 7
