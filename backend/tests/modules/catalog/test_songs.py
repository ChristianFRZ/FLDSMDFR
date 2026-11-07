import pytest

from app.modules.catalog import public


async def list_songs(client, user, query=""):
    return (await client.get(f"/api/songs{query}", headers=user.headers)).json()


async def test_list_fields(client, listener, make_song):
    await make_song()
    item = (await list_songs(client, listener))["items"][0]
    expected = {"id", "title", "artist", "artist_id", "album", "duration", "cover_url", "source", "license"}
    assert expected <= item.keys()
    assert item["artist"] == "Marea Baja"
    assert item["album"] == "Noches"


@pytest.mark.parametrize(
    "query,expected",
    [
        ("?q=luz", 1),
        ("?q=MAREA", 1),
        ("?q=nada", 0),
        ("?genre=rock", 1),
        ("?genre=jazz", 0),
        ("?artist=marea", 1),
        ("?tag=guitarra", 1),
        ("?source=local", 1),
        ("?source=jamendo", 0),
    ],
)
async def test_filters(client, listener, make_song, query, expected):
    await make_song()
    assert (await list_songs(client, listener, query))["total"] == expected


@pytest.mark.parametrize("status", ["hidden", "draft", "scheduled"])
async def test_unpublished_not_listed(client, listener, make_song, status):
    await make_song(status=status)
    assert (await list_songs(client, listener))["total"] == 0


async def test_pagination(client, listener, make_song):
    for i in range(5):
        await make_song(title=f"Pista {i}")
    r = await list_songs(client, listener, "?page=2&size=2")
    assert r["total"] == 5
    assert r["page"] == 2
    assert len(r["items"]) == 2


async def test_songs_requires_auth(client):
    assert (await client.get("/api/songs")).status_code == 401


async def test_song_detail(client, listener, make_song):
    song = await make_song()
    r = await client.get(f"/api/songs/{song.id}", headers=listener.headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Luz de carretera"


async def test_hidden_song_detail_404(client, listener, make_song):
    song = await make_song(status="hidden")
    assert (await client.get(f"/api/songs/{song.id}", headers=listener.headers)).status_code == 404


async def test_artist_page_lists_published_only(client, listener, make_song):
    song = await make_song()
    await make_song(title="Secreta", status="draft")
    r = (await client.get(f"/api/artists/{song.artist_id}", headers=listener.headers)).json()
    assert r["name"] == "Marea Baja"
    assert [s["title"] for s in r["songs"]] == ["Luz de carretera"]


async def test_genres_list(client, listener, make_song):
    await make_song(genres=("rock", "pop"))
    assert (await client.get("/api/genres", headers=listener.headers)).json() == ["pop", "rock"]


async def test_public_get_songs_marks_hidden_unavailable(make_song):
    visible = await make_song(title="A")
    hidden = await make_song(title="B", status="hidden")
    songs = await public.get_songs([visible.id, hidden.id])
    assert songs[visible.id].available is True
    assert songs[hidden.id].available is False
    assert songs[hidden.id].title == "B"


async def test_public_get_songs_empty():
    assert await public.get_songs([]) == {}


async def test_song_is_playable(make_song):
    assert await public.song_is_playable((await make_song()).id) is True
    assert await public.song_is_playable((await make_song(status="draft")).id) is False


async def test_catalog_by_source(make_song):
    await make_song(title="A")
    await make_song(title="B", artist="J", source="jamendo", jamendo_id="1")
    assert await public.catalog_by_source() == {"local": 1, "jamendo": 1}
