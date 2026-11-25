from datetime import UTC, datetime, timedelta
from uuid import uuid4

from catalog_streaming.main import create_app


async def test_internal_songs_returns_missing_ids_absent(client, make_song):
    song = await make_song()
    missing = uuid4()
    response = await client.get("/internal/songs", params={"ids": f"{song.id},{missing}"})
    assert response.status_code == 200
    body = response.json()
    assert list(body) == [str(song.id)]
    assert body[str(song.id)]["title"] == "Luz de carretera"


async def test_internal_songs_rejects_more_than_200_ids(client):
    ids = ",".join(str(uuid4()) for _ in range(201))
    response = await client.get("/internal/songs", params={"ids": ids})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    response = await client.get("/internal/artists", params={"ids": ids})
    assert response.status_code == 422


async def test_internal_playable_true_only_for_published(client, make_song):
    published = await make_song()
    scheduled = await make_song(title="Pronto", status="scheduled", publish_at=datetime.now(UTC) + timedelta(days=1))
    assert (await client.get(f"/internal/songs/{published.id}/playable")).json() == {"playable": True}
    assert (await client.get(f"/internal/songs/{scheduled.id}/playable")).json() == {"playable": False}
    assert (await client.get(f"/internal/songs/{uuid4()}/playable")).json() == {"playable": False}


async def test_internal_published_since_excludes_jamendo(client, make_song):
    now = datetime.now(UTC)
    local = await make_song(artist="Local", published_at=now)
    jamendo = await make_song(artist="Remoto", source="jamendo", published_at=now)
    ids = f"{local.artist_id},{jamendo.artist_id}"
    response = await client.get("/internal/artists/published-since", params={"artist_ids": ids, "since": ""})
    assert response.status_code == 200
    assert [r["song"]["id"] for r in response.json()] == [str(local.id)]
    later = (now + timedelta(hours=1)).isoformat()
    response = await client.get("/internal/artists/published-since", params={"artist_ids": ids, "since": later})
    assert response.json() == []


async def test_internal_upcoming_owners_and_counts(client, make_song):
    owner = uuid4()
    soon = datetime.now(UTC) + timedelta(days=1)
    scheduled = await make_song(status="scheduled", publish_at=soon, owner=owner)
    published = await make_song(title="Ya", owner=owner)
    upcoming = (await client.get("/internal/artists/upcoming", params={"artist_ids": str(scheduled.artist_id)})).json()
    assert [u["song_id"] for u in upcoming] == [str(scheduled.id)]
    owned = (await client.get(f"/internal/owners/{owner}/songs")).json()
    assert set(owned) == {str(scheduled.id), str(published.id)}
    counts = (await client.get("/internal/catalog/release-counts", params={"owner_id": str(owner)})).json()
    assert counts == {"scheduled": 1, "published": 1}
    assert (await client.get("/internal/catalog/release-counts")).json() == {"scheduled": 1, "published": 1}
    assert (await client.get("/internal/catalog/by-source")).json() == {"local": 1}
    artists = (await client.get("/internal/artists", params={"ids": str(published.artist_id)})).json()
    assert artists[str(published.artist_id)]["name"] == "Marea Baja"


async def test_internal_jamendo_status_and_health(client, monkeypatch):
    async def fake_ask():
        return "up"

    monkeypatch.setattr("catalog_streaming.modules.catalog.public._ask_jamendo", fake_ask)
    assert (await client.get("/internal/jamendo-status")).json() == {"status": "up"}
    health = (await client.get("/internal/health")).json()
    assert health["name"] == "catalog-streaming"
    assert health["status"] == "up"
    assert isinstance(health["database_ms"], float)
    assert isinstance(health["uptime_seconds"], int)


async def test_internal_demo_catalog_roundtrip(client):
    owner = str(uuid4())
    body = {"composers": [{"user_id": owner, "name": "Demo", "bio": "bio", "tracks": [
        {"title": "T1", "genre": "rock", "audio_path": "demo/t1.mp3", "duration": 100.0, "status": "published",
         "publish_at": None, "published_at": datetime.now(UTC).isoformat()}]}]}
    assert (await client.post("/internal/demo/catalog", json=body)).status_code == 204
    listenable = (await client.get("/internal/demo/catalog/listenable", params={"limit": 5})).json()
    assert len(listenable) == 1 and listenable[0]["source"] == "local"
    assert (await client.get("/internal/catalog/by-source")).json() == {"local": 1}
    assert (await client.get("/internal/demo/catalog/import-done", params={"genres": "rock", "minimum": 1})).json() == {"done": False}
    assert (await client.post("/internal/demo/catalog/clear")).status_code == 204
    assert (await client.get("/internal/catalog/by-source")).json() == {}


def test_internal_routes_have_no_public_prefix():
    from catalog_streaming.internal_routes import router

    assert router.routes
    assert all(route.path.startswith("/internal") for route in router.routes)
    paths = set(create_app().openapi()["paths"])
    assert "/internal/songs" in paths and "/internal/latency/drain" in paths
