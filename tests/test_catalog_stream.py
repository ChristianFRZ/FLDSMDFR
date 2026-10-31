import uuid

from tests.audio_fixtures import insert_song
from tests.helpers import signup


async def test_list_songs_requires_session(client):
    assert (await client.get("/api/songs")).status_code == 401


async def test_list_and_search(client, session, media_dir):
    await signup(client)
    await insert_song(session, media_dir, title="Nubes de agosto", artist="Los Meteoros")
    await insert_song(session, media_dir, title="Rayo lento", artist="Los Meteoros")
    await insert_song(session, media_dir, title="Marea", artist="Otra Banda")
    await insert_song(session, media_dir, title="Oculta", artist="Los Meteoros", is_active=False)

    everything = (await client.get("/api/songs")).json()
    assert everything["total"] == 3
    assert [s["title"] for s in everything["items"]] == ["Marea", "Nubes de agosto", "Rayo lento"]

    found = (await client.get("/api/songs", params={"q": "meteoros"})).json()
    assert found["total"] == 2
    assert {s["artist"] for s in found["items"]} == {"Los Meteoros"}

    page = (await client.get("/api/songs", params={"limit": 1, "offset": 1})).json()
    assert page["total"] == 3
    assert [s["title"] for s in page["items"]] == ["Nubes de agosto"]


async def test_list_limit_validated(client):
    await signup(client)
    assert (await client.get("/api/songs", params={"limit": 0})).status_code == 422
    assert (await client.get("/api/songs", params={"limit": 101})).status_code == 422
    assert (await client.get("/api/songs", params={"offset": -1})).status_code == 422


async def test_search_wildcards_are_literal(client, session, media_dir):
    await signup(client)
    await insert_song(session, media_dir, title="100% Lluvia")
    await insert_song(session, media_dir, title="Lluvia")

    pct = (await client.get("/api/songs", params={"q": "%"})).json()
    assert [s["title"] for s in pct["items"]] == ["100% Lluvia"]
    under = (await client.get("/api/songs", params={"q": "_"})).json()
    assert under["total"] == 0 and under["items"] == []


async def test_get_song(client, session, media_dir):
    await signup(client)
    song = await insert_song(session, media_dir)
    r = await client.get(f"/api/songs/{song.id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Nubes de agosto"


async def _stream_setup(client, session, media_dir, **kwargs):
    await signup(client)
    song = await insert_song(session, media_dir, **kwargs)
    return song, (media_dir / f"{song.id}.wav").read_bytes()


async def test_stream_full(client, session, media_dir):
    song, data = await _stream_setup(client, session, media_dir)
    r = await client.get(f"/api/songs/{song.id}/stream")
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == data


async def test_stream_partial(client, session, media_dir):
    song, data = await _stream_setup(client, session, media_dir)
    r = await client.get(f"/api/songs/{song.id}/stream", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 0-99/{len(data)}"
    assert r.headers["content-length"] == "100"
    assert r.headers["accept-ranges"] == "bytes"
    assert len(r.content) == 100
    assert r.content == data[0:100]


async def test_stream_suffix(client, session, media_dir):
    song, data = await _stream_setup(client, session, media_dir)
    r = await client.get(f"/api/songs/{song.id}/stream", headers={"Range": "bytes=-50"})
    assert r.status_code == 206
    assert r.content == data[-50:]


async def test_stream_multirange_serves_full(client, session, media_dir):
    song, data = await _stream_setup(client, session, media_dir)
    r = await client.get(f"/api/songs/{song.id}/stream", headers={"Range": "bytes=0-1,4-5"})
    assert r.status_code == 200
    assert r.content == data


async def test_stream_unsatisfiable(client, session, media_dir):
    song, data = await _stream_setup(client, session, media_dir)
    r = await client.get(f"/api/songs/{song.id}/stream", headers={"Range": f"bytes={len(data)}-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(data)}"
    assert r.json()["error"]["code"] == "range_not_satisfiable"


async def test_stream_requires_session(client, session, media_dir):
    song = await insert_song(session, media_dir)
    assert (await client.get(f"/api/songs/{song.id}/stream")).status_code == 401


async def test_stream_inactive_song_404(client, session, media_dir):
    await signup(client)
    song = await insert_song(session, media_dir, is_active=False)
    assert (await client.get(f"/api/songs/{song.id}/stream")).status_code == 404
    assert (await client.get(f"/api/songs/{song.id}")).status_code == 404


async def test_stream_unknown_song_404(client):
    await signup(client)
    assert (await client.get(f"/api/songs/{uuid.uuid4()}/stream")).status_code == 404


async def test_stream_missing_file_404(client, session, media_dir):
    song, _ = await _stream_setup(client, session, media_dir)
    (media_dir / f"{song.id}.wav").unlink()
    assert (await client.get(f"/api/songs/{song.id}/stream")).status_code == 404
