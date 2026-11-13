from uuid import uuid4

import pytest
from meloxo_common.internal import UpstreamError

from users_playlists.clients import catalog


async def test_get_songs_250_ids_makes_two_calls_and_returns_all(fake_catalog):
    songs = [fake_catalog.add_song(title=f"Pista {i}") for i in range(250)]
    found = await catalog.get_songs([s.id for s in songs])
    assert len(found) == 250
    assert [len(c.url.params["ids"].split(",")) for c in fake_catalog.calls] == [200, 50]


async def test_get_songs_without_ids_does_not_call_catalog(fake_catalog):
    assert await catalog.get_songs([]) == {}
    assert fake_catalog.calls == []


async def test_get_songs_omits_unknown_ids(fake_catalog):
    song = fake_catalog.add_song()
    found = await catalog.get_songs([song.id, uuid4()])
    assert list(found) == [song.id]


async def test_get_artists_batches_and_merges(fake_catalog):
    songs = [fake_catalog.add_song(artist=f"Artista {i}") for i in range(250)]
    found = await catalog.get_artists([s.artist_id for s in songs])
    assert len(found) == 250
    assert len(fake_catalog.calls) == 2


async def test_song_is_playable_and_owner_songs(fake_catalog):
    owner = uuid4()
    song = fake_catalog.add_song(owner=owner)
    hidden = fake_catalog.add_song(title="Oculta", status="hidden", owner=owner)
    assert await catalog.song_is_playable(song.id) is True
    assert await catalog.song_is_playable(hidden.id) is False
    assert set(await catalog.songs_owned_by(owner)) == {song.id, hidden.id}


@pytest.mark.parametrize(
    "call",
    [
        lambda: catalog.get_songs([uuid4()]),
        lambda: catalog.get_artists([uuid4()]),
        lambda: catalog.upcoming_for_artists([uuid4()]),
        lambda: catalog.published_since([uuid4()], None),
        lambda: catalog.song_is_playable(uuid4()),
        lambda: catalog.songs_owned_by(uuid4()),
    ],
)
async def test_every_call_raises_upstream_error_when_catalog_is_down(fake_catalog, call):
    fake_catalog.down = True
    with pytest.raises(UpstreamError):
        await call()
