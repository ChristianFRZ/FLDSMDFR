"""El gateway: única puerta, reparte por prefijo y en round-robin entre instancias vivas."""

import pytest

from tests.conftest import AUDIO


@pytest.mark.parametrize(
    ("path", "service"),
    [
        ("/api/auth/login", "users-playlists"),
        ("/api/playlists/abc", "users-playlists"),
        ("/api/me/favorites", "users-playlists"),
        ("/api/me/history", "playback-metrics"),
        ("/api/playbacks", "playback-metrics"),
        ("/api/metrics/top", "playback-metrics"),
        ("/api/songs", "catalog-streaming"),
        ("/", "web"),
        ("/casetes/xyz", "web"),
    ],
)
async def test_routes_by_prefix(client, cluster, path, service):
    r = await client.get(path)
    assert r.status_code == 200
    assert r.json()["label"].startswith(service + "@")
    assert r.json()["path"] == path


async def test_query_string_is_forwarded(client, cluster):
    r = await client.get("/api/songs?q=lluvia&limit=5")
    assert r.json()["query"] == "q=lluvia&limit=5"


async def test_round_robin_alternates_instances(client, cluster):
    labels = [(await client.get("/api/songs")).headers["X-Instancia"] for _ in range(4)]
    assert labels == [
        "catalog-streaming@10.0.4.1",
        "catalog-streaming@10.0.4.2",
        "catalog-streaming@10.0.4.1",
        "catalog-streaming@10.0.4.2",
    ]


async def test_gateway_marks_itself(client, cluster):
    r = await client.get("/api/songs")
    assert r.headers["X-Gateway-Instancia"].startswith("gateway-")


async def test_no_instances_503(client, consul, network):
    r = await client.get("/api/songs")
    assert r.status_code == 503
    body = r.json()["error"]
    assert body["code"] == "service_unavailable"
    assert "catalog-streaming" in body["message"]


async def test_connect_error_503(client, cluster):
    """Réplica muerta que la caché del balanceador todavía anuncia: sin reintento en 03."""
    _consul, network = cluster
    del network.hosts["10.0.4.1"]
    codes = [(await client.get("/api/songs")).status_code for _ in range(2)]
    assert sorted(codes) == [200, 503]


async def test_internal_is_404(client, cluster):
    r = await client.get("/internal/users/count")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


async def test_range_passthrough_206(client, cluster):
    r = await client.get("/api/songs/abc/stream", headers={"Range": "bytes=0-1023"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 0-1023/{len(AUDIO)}"
    assert r.headers["content-length"] == "1024"
    assert r.content == AUDIO[:1024]


async def test_multiple_set_cookie_preserved(client, cluster):
    r = await client.post("/api/auth/login", json={})
    cookies = r.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert any(c.startswith("fldsmdfr_session=") for c in cookies)


async def test_upload_body_is_forwarded(client, cluster):
    r = await client.post("/api/songs", content=b"x" * 50_000)
    assert r.json()["bytes"] == 50_000


async def test_upload_over_limit_json(client, cluster):
    big = {"Content-Length": str(22 * 1024 * 1024)}
    songs = await client.post("/api/songs", headers=big, content=b"")
    assert (songs.status_code, songs.json()["error"]["code"]) == (422, "file_too_large")
    cover = await client.put("/api/playlists/abc/cover", headers=big, content=b"")
    assert (cover.status_code, cover.json()["error"]["code"]) == (413, "image_too_large")


async def test_lb_cache_hides_new_instances(client, cluster):
    consul, network = cluster
    await client.get("/api/me/history")
    consul.add("playback-metrics", "playback-metrics-new", "10.0.2.2")
    network.add("10.0.2.2", "playback-metrics@10.0.2.2")
    labels = {(await client.get("/api/me/history")).headers["X-Instancia"] for _ in range(4)}
    assert labels == {"playback-metrics@10.0.2.1"}


async def test_health_reports_directory(client, consul):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
