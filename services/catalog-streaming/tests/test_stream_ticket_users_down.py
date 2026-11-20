from pathlib import Path
from uuid import uuid4

from catalog_streaming.auth import auth_state_cache
from catalog_streaming.config import get_settings

AUDIO = bytes(range(256)) * 4


async def _song_and_ticket(client, make_song, listener):
    name = f"audio/{uuid4()}.mp3"
    path = Path(get_settings().MEDIA_DIR) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(AUDIO)
    song = await make_song(audio_path=name)
    r = await client.post(f"/api/songs/{song.id}/stream-ticket", headers=listener.headers)
    return song, r.json()["ticket"]


async def test_signed_ticket_works_with_users_down_and_cold_cache(client, listener, make_song, users_service):
    song, ticket = await _song_and_ticket(client, make_song, listener)
    auth_state_cache.clear()
    users_service.down = True
    r = await client.get(f"/api/songs/{song.id}/stream?ticket={ticket}")
    assert r.status_code == 200
    assert r.content == AUDIO


async def test_signed_ticket_works_with_users_down_and_stored_state(client, listener, make_song, users_service):
    song, ticket = await _song_and_ticket(client, make_song, listener)
    users_service.down = True
    r = await client.get(f"/api/songs/{song.id}/stream?ticket={ticket}", headers={"Range": "bytes=0-9"})
    assert r.status_code == 206


async def test_suspended_account_ticket_rejected_when_users_reachable(client, listener, make_song, users_service):
    song, ticket = await _song_and_ticket(client, make_song, listener)
    users_service.set_status(listener, "suspended")
    assert (await client.get(f"/api/songs/{song.id}/stream?ticket={ticket}")).status_code == 401


async def test_ticket_of_unknown_user_rejected_when_users_reachable(client, listener, make_song, users_service):
    song, ticket = await _song_and_ticket(client, make_song, listener)
    del users_service.users[listener.id]
    auth_state_cache.clear()
    assert (await client.get(f"/api/songs/{song.id}/stream?ticket={ticket}")).status_code == 401


async def test_bad_ticket_still_rejected_with_users_down(client, listener, make_song, users_service):
    song, _ = await _song_and_ticket(client, make_song, listener)
    users_service.down = True
    assert (await client.get(f"/api/songs/{song.id}/stream?ticket=basura")).status_code == 401
