from datetime import UTC, datetime
from uuid import uuid4

from users_playlists.main import create_app


async def _playlist(client, user, name="Mía"):
    return (await client.post("/api/playlists", json={"name": name}, headers=user.headers)).json()


async def _add(client, user, playlist, song):
    r = await client.post(f"/api/playlists/{playlist['id']}/songs", json={"song_id": str(song.id)}, headers=user.headers)
    assert r.status_code == 201, r.text


async def test_auth_state_returns_role_and_status(client, listener):
    r = await client.get(f"/internal/users/{listener.id}/auth-state")
    assert r.status_code == 200
    assert r.json() == {"id": listener.id, "role": "listener", "status": "active"}


async def test_auth_state_404_for_unknown_user(client):
    r = await client.get(f"/internal/users/{uuid4()}/auth-state")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


async def test_auth_state_malformed_id_is_422(client):
    assert (await client.get("/internal/users/no-es-uuid/auth-state")).status_code == 422


async def test_display_names_returns_known_only(client, listener):
    r = await client.get("/internal/users/display-names", params={"ids": f"{listener.id},{uuid4()}"})
    assert r.status_code == 200
    assert r.json() == {listener.id: listener.email.split("@")[0]}


async def test_display_names_rejects_more_than_200_ids(client):
    ids = ",".join(str(uuid4()) for _ in range(201))
    r = await client.get("/internal/users/display-names", params={"ids": ids})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


async def test_malformed_ids_are_422(client):
    assert (await client.get("/internal/users/display-names", params={"ids": "x"})).status_code == 422
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": "x"})).status_code == 422
    assert (await client.get("/internal/tapes/inclusions", params={"song_ids": "x"})).status_code == 422


async def test_audit_post_writes_entry_visible_in_admin_audit(client, admin):
    body = {"actor_id": admin.id, "action": "song_hidden", "target_type": "song", "target_id": "abc", "detail": {"why": "x"}}
    r = await client.post("/internal/audit", json=body)
    assert r.status_code == 204
    assert r.content == b""
    items = (await client.get("/api/admin/audit?action=song_hidden", headers=admin.headers)).json()["items"]
    assert len(items) == 1
    assert items[0]["target_id"] == "abc"
    assert items[0]["outcome"] == "ok"


async def test_audit_rejects_incomplete_body(client):
    assert (await client.post("/internal/audit", json={"action": "x"})).status_code == 422


async def test_inclusions_count_distinct_playlists(client, listener, make_song):
    first, second, other = await make_song(), await make_song(title="Dos"), await make_song(title="Tres")
    a, b = await _playlist(client, listener, "A"), await _playlist(client, listener, "B")
    await _add(client, listener, a, first)
    await _add(client, listener, a, second)
    await _add(client, listener, b, first)
    ids = f"{first.id},{second.id}"
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": ids})).json() == {"count": 2}
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": str(second.id)})).json() == {"count": 1}
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": str(other.id)})).json() == {"count": 0}
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": ""})).json() == {"count": 0}


async def test_tape_inclusions_and_activity(client, listener, make_song):
    song, other = await make_song(), await make_song(title="Dos")
    tape = (await client.post("/api/tapes", json={"title": "Viaje"}, headers=listener.headers)).json()
    for track, dedication in ((song, "Para ti"), (other, None)):
        body = {"song_id": str(track.id), **({"dedication": dedication} if dedication else {})}
        r = await client.post(f"/api/tapes/{tape['id']}/tracks", json=body, headers=listener.headers)
        assert r.status_code == 201, r.text
    assert (await client.get("/internal/tapes/inclusions", params={"song_ids": str(song.id)})).json() == {"count": 1}
    assert (await client.get("/internal/tapes/activity")).json() == {"tapes": 1, "members": 1, "tracks": 2, "dedications": 1}


async def test_growth_counts_users_per_day(client, listener, composer):
    r = await client.get("/internal/users/growth", params={"days": 3})
    assert r.status_code == 200
    points = r.json()
    assert len(points) == 3
    today = datetime.now(UTC).date().isoformat()
    assert points[-1] == {"day": today, "listener": 1, "composer": 1, "admin": 0}


async def test_health_shape(client):
    body = (await client.get("/internal/health")).json()
    assert body["name"] == "users-playlists"
    assert body["status"] == "up"
    assert body["database_ms"] >= 0
    assert body["uptime_seconds"] >= 0


async def test_latency_drain_is_mounted(client):
    assert (await client.post("/internal/latency/drain")).status_code == 200


async def test_internal_routes_have_no_public_prefix():
    from users_playlists.internal_routes import router

    assert router.routes
    assert all(route.path.startswith("/internal/") for route in router.routes)
    published = set(create_app().openapi()["paths"])
    assert {route.path for route in router.routes} <= published


async def test_demo_users_round_trip(client):
    body = {
        "password": "demo12345",
        "users": [
            {"email": "ana@demo.test", "display_name": "Ana", "role": "composer", "created_at": "2026-01-02T03:04:05Z", "request_message": None},
            {"email": "leo@demo.test", "display_name": "Leo", "role": "listener", "created_at": "2026-01-03T00:00:00Z"},
        ],
    }
    r = await client.post("/internal/demo/users", json=body)
    assert r.status_code == 200
    ids = r.json()["ids"]
    assert set(ids) == {"ana@demo.test", "leo@demo.test"}
    listed = (await client.get("/internal/demo/users/ids")).json()
    assert set(listed["ids"]) == set(ids.values())
    assert (await client.get(f"/internal/users/{ids['ana@demo.test']}/auth-state")).json()["role"] == "composer"
    assert (await client.post("/internal/demo/users/clear")).status_code == 204
    assert (await client.get("/internal/demo/users/ids")).json() == {"ids": []}


async def test_demo_playlists_and_social_round_trip(client, listener, make_song):
    song = await make_song()
    playlist = {"owner_id": listener.id, "name": "Demo", "is_public": True, "song_ids": [str(song.id)]}
    assert (await client.post("/internal/demo/playlists", json={"playlists": [playlist]})).status_code == 204
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": str(song.id)})).json() == {"count": 1}
    tape = {
        "creator_id": listener.id, "title": "Demo", "color": "amber", "member_ids": [listener.id],
        "tracks": [{"song_id": str(song.id), "added_by": listener.id, "dedication": "hola"}],
    }
    assert (await client.post("/internal/demo/social", json={"tapes": [tape], "favorites": [[listener.id, str(song.id)]], "follows": [[listener.id, str(uuid4())]]})).status_code == 204
    assert (await client.get("/internal/tapes/activity")).json()["tapes"] == 1
    assert (await client.post("/internal/demo/social/clear", json={"user_ids": [listener.id]})).status_code == 204
    assert (await client.get("/internal/tapes/activity")).json()["tapes"] == 0
    assert (await client.post("/internal/demo/playlists/clear")).status_code == 204
    assert (await client.get("/internal/playlists/inclusions", params={"song_ids": str(song.id)})).json() == {"count": 0}
