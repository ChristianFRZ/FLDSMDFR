import asyncio

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import session_scope
from app.modules.social import public
from app.modules.social.models import TapeTrack


async def make_tape(client, user, title="Para el viaje", **kw):
    r = await client.post("/api/tapes", json={"title": title, **kw}, headers=user.headers)
    assert r.status_code == 201, r.text
    return r.json()


async def add_track(client, user, tape, song, dedication=None):
    body = {"song_id": str(song.id)}
    if dedication is not None:
        body["dedication"] = dedication
    return await client.post(f"/api/tapes/{tape['id']}/tracks", json=body, headers=user.headers)


async def read(client, user, tape):
    return await client.get(f"/api/tapes/{tape['id']}", headers=user.headers)


async def join(client, tape, owner, user):
    r = await client.post(f"/api/tapes/{tape['id']}/invites", json={"max_uses": 1}, headers=owner.headers)
    r = await client.post(f"/api/tapes/join/{r.json()['token']}", headers=user.headers)
    assert r.status_code == 200, r.text


async def count_tracks(tape):
    async with session_scope() as session:
        return await session.scalar(
            select(func.count()).select_from(TapeTrack).where(TapeTrack.tape_id == tape["id"])
        )


async def fill(client, user, tape, make_song, n):
    return [
        (await add_track(client, user, tape, await make_song(title=f"Pista {i}"))).json()
        for i in range(n)
    ]


async def test_creator_is_member(client, listener):
    tape = await make_tape(client, listener)
    body = (await read(client, listener, tape)).json()
    assert [m["user_id"] for m in body["members"]] == [listener.id]
    assert body["is_creator"] is True


async def test_list_only_my_tapes(client, listener, make_user):
    other = await make_user()
    await make_tape(client, listener)
    await make_tape(client, other, title="Ajeno")
    body = (await client.get("/api/tapes", headers=listener.headers)).json()
    assert [t["title"] for t in body] == ["Para el viaje"]
    assert body[0]["track_count"] == 0
    assert body[0]["member_count"] == 1
    assert body[0]["max_tracks"] == 12


async def test_unknown_color_422(client, listener):
    r = await client.post("/api/tapes", json={"title": "x", "color": "verde"}, headers=listener.headers)
    assert r.status_code == 422


async def test_hex_color_is_saved(client, listener):
    r = await client.post("/api/tapes", json={"title": "x", "color": "#1a2B3c"}, headers=listener.headers)
    assert r.status_code == 201
    assert r.json()["color"] == "#1a2B3c"


@pytest.mark.parametrize("color", ["#12345", "#1234567", "#12345g", "123456"])
async def test_malformed_hex_color_422(client, listener, color):
    r = await client.post("/api/tapes", json={"title": "x", "color": color}, headers=listener.headers)
    assert r.status_code == 422


async def test_non_member_403(client, listener, make_user, make_song):
    other, song = await make_user(), await make_song()
    tape = await make_tape(client, listener)
    assert (await read(client, other, tape)).status_code == 403
    assert (await add_track(client, other, tape, song)).status_code == 403


async def test_only_creator_deletes(client, listener, make_user):
    other = await make_user()
    tape = await make_tape(client, listener)
    await join(client, tape, listener, other)
    url = f"/api/tapes/{tape['id']}"
    assert (await client.delete(url, headers=other.headers)).status_code == 403
    assert (await client.delete(url, headers=listener.headers)).status_code == 204
    assert (await client.get(url, headers=listener.headers)).status_code == 404


async def test_only_creator_edits(client, listener, make_user):
    other = await make_user()
    tape = await make_tape(client, listener)
    await join(client, tape, listener, other)
    url = f"/api/tapes/{tape['id']}"
    assert (await client.patch(url, json={"title": "x"}, headers=other.headers)).status_code == 403
    r = await client.patch(url, json={"title": "Nuevo"}, headers=listener.headers)
    assert r.json()["title"] == "Nuevo"


async def test_track_12_race_one_wins(client, listener, make_user, make_song):
    other = await make_user()
    tape = await make_tape(client, listener)
    await join(client, tape, listener, other)
    await fill(client, listener, tape, make_song, 11)
    a, b = await make_song(title="Última A"), await make_song(title="Última B")
    r = await asyncio.gather(add_track(client, listener, tape, a), add_track(client, other, tape, b))
    assert sorted(x.status_code for x in r) == [201, 409]
    assert await count_tracks(tape) == 12


async def test_same_song_twice_409(client, listener, make_song):
    song, tape = await make_song(), await make_tape(client, listener)
    await add_track(client, listener, tape, song)
    r = await add_track(client, listener, tape, song)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "song_already_in_tape"


async def test_unknown_song_404(client, listener):
    from types import SimpleNamespace
    from uuid import uuid4

    tape = await make_tape(client, listener)
    assert (await add_track(client, listener, tape, SimpleNamespace(id=uuid4()))).status_code == 404


async def test_hidden_song_cannot_be_added(client, admin, listener, make_song):
    song, tape = await make_song(), await make_tape(client, listener)
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    assert (await add_track(client, listener, tape, song)).status_code == 409


async def test_dedication_141_chars_422(client, listener, make_song):
    song, tape = await make_song(), await make_tape(client, listener)
    assert (await add_track(client, listener, tape, song, "x" * 141)).status_code == 422
    assert (await add_track(client, listener, tape, song, "x" * 140)).status_code == 201


async def test_dedication_visible_to_members(client, listener, make_user, make_song):
    other, song = await make_user(), await make_song()
    tape = await make_tape(client, listener)
    await join(client, tape, listener, other)
    await add_track(client, listener, tape, song, "Para ti")
    track = (await read(client, other, tape)).json()["tracks"][0]
    assert track["dedication"] == "Para ti"
    assert track["added_by"] == listener.id


async def test_remove_only_adder_or_creator(client, listener, make_user, make_song):
    adder, bystander = await make_user(), await make_user()
    tape = await make_tape(client, listener)
    await join(client, tape, listener, adder)
    await join(client, tape, listener, bystander)
    first = (await add_track(client, adder, tape, await make_song(title="A"))).json()
    second = (await add_track(client, adder, tape, await make_song(title="B"))).json()
    base = f"/api/tapes/{tape['id']}/tracks"
    assert (await client.delete(f"{base}/{first['id']}", headers=bystander.headers)).status_code == 403
    assert (await client.delete(f"{base}/{first['id']}", headers=adder.headers)).status_code == 204
    assert (await client.delete(f"{base}/{second['id']}", headers=listener.headers)).status_code == 204


async def test_remove_compacts_positions(client, listener, make_song):
    tape = await make_tape(client, listener)
    tracks = await fill(client, listener, tape, make_song, 3)
    await client.delete(f"/api/tapes/{tape['id']}/tracks/{tracks[0]['id']}", headers=listener.headers)
    body = (await read(client, listener, tape)).json()
    assert [t["position"] for t in body["tracks"]] == [1, 2]


async def reorder(client, user, tape, version, ids):
    return await client.put(
        f"/api/tapes/{tape['id']}/order", json={"version": version, "track_ids": ids}, headers=user.headers
    )


async def test_any_member_reorders(client, listener, make_user, make_song):
    other = await make_user()
    tape = await make_tape(client, listener)
    await join(client, tape, listener, other)
    tracks = await fill(client, listener, tape, make_song, 2)
    body = (await read(client, other, tape)).json()
    ids = [tracks[1]["id"], tracks[0]["id"]]
    assert (await reorder(client, other, tape, body["version"], ids)).status_code == 200
    assert [t["id"] for t in (await read(client, other, tape)).json()["tracks"]] == ids


async def test_reorder_with_stale_version_409(client, listener, make_song):
    tape = await make_tape(client, listener)
    tracks = await fill(client, listener, tape, make_song, 2)
    version = (await read(client, listener, tape)).json()["version"]
    ids = [t["id"] for t in tracks]
    assert (await reorder(client, listener, tape, version, ids[::-1])).status_code == 200
    r = await reorder(client, listener, tape, version, ids)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "tape_version_conflict"


async def test_concurrent_reorder_one_wins(client, listener, make_song):
    tape = await make_tape(client, listener)
    tracks = await fill(client, listener, tape, make_song, 3)
    version = (await read(client, listener, tape)).json()["version"]
    ids = [t["id"] for t in tracks]
    r = await asyncio.gather(
        reorder(client, listener, tape, version, ids[::-1]),
        reorder(client, listener, tape, version, ids[1:] + ids[:1]),
    )
    assert sorted(x.status_code for x in r) == [200, 409]


async def test_reorder_needs_exact_tracks_422(client, listener, make_song):
    tape = await make_tape(client, listener)
    tracks = await fill(client, listener, tape, make_song, 2)
    version = (await read(client, listener, tape)).json()["version"]
    assert (await reorder(client, listener, tape, version, [tracks[0]["id"]])).status_code == 422


async def test_side_is_position(client, listener, make_song):
    tape = await make_tape(client, listener)
    await fill(client, listener, tape, make_song, 12)
    tracks = (await read(client, listener, tape)).json()["tracks"]
    assert [t["side"] for t in tracks] == ["A"] * 6 + ["B"] * 6


async def test_hidden_track_keeps_slot_and_dedication(client, admin, listener, make_song):
    tape = await make_tape(client, listener)
    song = await make_song(title="Oculta")
    await add_track(client, listener, tape, song, "Te la dejo")
    await add_track(client, listener, tape, await make_song(title="Otra"))
    await client.post(f"/api/admin/songs/{song.id}/hide", json={"reason": "x"}, headers=admin.headers)
    first = (await read(client, listener, tape)).json()["tracks"][0]
    assert first["position"] == 1
    assert first["dedication"] == "Te la dejo"
    assert first["song"]["available"] is False


async def test_deleted_song_keeps_slot_from_cache(client, listener, composer):
    from tests.media import mp3

    r = await client.post(
        "/api/composer/tracks",
        data={"title": "Se va", "genre": "rock", "license": "CC"},
        files={"audio": ("a.mp3", mp3())},
        headers=composer.headers,
    )
    song_id = r.json()["id"]
    await client.post(f"/api/composer/tracks/{song_id}/publish", headers=composer.headers)
    tape = await make_tape(client, listener)
    await client.post(
        f"/api/tapes/{tape['id']}/tracks", json={"song_id": song_id, "dedication": "Hola"}, headers=listener.headers
    )
    await client.delete(f"/api/composer/tracks/{song_id}", headers=composer.headers)
    track = (await read(client, listener, tape)).json()["tracks"][0]
    assert track["song"]["title"] == "Se va"
    assert track["song"]["available"] is False
    assert track["dedication"] == "Hola"


async def test_catalog_down_tape_is_degraded(client, listener, make_song, monkeypatch):
    from app.modules.social import tapes

    song, tape = await make_song(), await make_tape(client, listener)
    await add_track(client, listener, tape, song)

    async def broken(_):
        raise RuntimeError("catálogo caído")

    monkeypatch.setattr(tapes, "get_songs", broken)
    body = (await read(client, listener, tape)).json()
    assert body["degraded"] is True
    assert body["tracks"][0]["song"]["title"] == "Luz de carretera"
    assert (await add_track(client, listener, tape, song)).status_code == 503


async def test_limits_configurable(client, listener, make_song, monkeypatch):
    monkeypatch.setattr(get_settings(), "TAPE_MAX_TRACKS", 4)
    tape = await make_tape(client, listener)
    await fill(client, listener, tape, make_song, 4)
    assert (await add_track(client, listener, tape, await make_song(title="Sobra"))).status_code == 409
    tracks = (await read(client, listener, tape)).json()["tracks"]
    assert [t["side"] for t in tracks] == ["A", "A", "B", "B"]


@pytest.mark.parametrize("dedications", [0, 1])
async def test_tape_activity(client, listener, make_song, dedications):
    tape = await make_tape(client, listener)
    await add_track(client, listener, tape, await make_song(), "Hola" if dedications else None)
    stats = await public.tape_activity()
    assert (stats.tapes, stats.members, stats.tracks, stats.dedications) == (1, 1, 1, dedications)


async def test_count_tape_inclusions(client, listener, make_song):
    song = await make_song()
    for title in ("A", "B"):
        await add_track(client, listener, await make_tape(client, listener, title=title), song)
    assert await public.count_tape_inclusions([song.id]) == 2
