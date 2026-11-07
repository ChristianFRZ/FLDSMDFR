from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import respx

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import create_token
from app.modules.catalog.streaming import parse_range

AUDIO = bytes(range(256)) * 4  # 1024 bytes
JAMENDO_URL = "https://audio.example/track?from=abc"


@pytest.fixture
async def local_song(make_song):
    name = f"audio/{uuid4()}.mp3"
    path = Path(get_settings().MEDIA_DIR) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(AUDIO)
    return await make_song(audio_path=name)


@pytest.fixture
async def jamendo_song(make_song):
    return await make_song(artist="J", source="jamendo", jamendo_id="9", audio_url=JAMENDO_URL)


def stream(client, song, user, headers=None):
    return client.get(f"/api/songs/{song.id}/stream", headers={**user.headers, **(headers or {})})


HUGE = "9" * 5000


@pytest.mark.parametrize(
    "header,size,expected",
    [
        (f"bytes=-{HUGE}", 1000, (0, 999)),
        (f"bytes=0-{HUGE}", 1000, (0, 999)),
        ("bytes=0-99", 1000, (0, 99)),
        ("bytes=500-", 1000, (500, 999)),
        ("bytes=-100", 1000, (900, 999)),
        ("bytes=-2000", 1000, (0, 999)),
        ("bytes=0-5000", 1000, (0, 999)),
        (None, 1000, None),
    ],
)
def test_parse_range_valid(header, size, expected):
    assert parse_range(header, size) == expected


@pytest.mark.parametrize("header", ["bytes=2000-", "bytes=9-1", "bytes=abc", "bytes=0-1,5-6", "bytes=-0", "items=0-1"])
def test_parse_range_invalid(header):
    with pytest.raises(AppError) as err:
        parse_range(header, 1000)
    assert err.value.status == 416


async def test_local_206(client, listener, local_song):
    r = await stream(client, local_song, listener, {"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 0-99/1024"
    assert r.headers["content-length"] == "100"
    assert r.content == AUDIO[:100]


async def test_local_range_from_middle_to_end(client, listener, local_song):
    r = await stream(client, local_song, listener, {"Range": "bytes=1000-"})
    assert r.status_code == 206
    assert r.content == AUDIO[1000:]


async def test_local_full_200(client, listener, local_song):
    r = await stream(client, local_song, listener)
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == AUDIO


async def test_local_invalid_range_416(client, listener, local_song):
    r = await stream(client, local_song, listener, {"Range": "bytes=5000-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == "bytes */1024"


async def test_missing_file_404(client, listener, make_song):
    song = await make_song(audio_path="audio/no-existe.mp3")
    r = await stream(client, song, listener)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "audio_missing"


@respx.mock
async def test_jamendo_proxy_206(client, listener, jamendo_song):
    route = respx.get(JAMENDO_URL).mock(
        return_value=httpx.Response(
            206,
            content=AUDIO[:100],
            headers={"Content-Range": "bytes 0-99/1024", "Content-Type": "audio/mpeg", "Content-Length": "100"},
        )
    )
    r = await stream(client, jamendo_song, listener, {"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert r.headers["content-range"] == "bytes 0-99/1024"
    assert r.content == AUDIO[:100]
    assert route.calls[0].request.headers["range"] == "bytes=0-99"


@respx.mock
async def test_jamendo_timeout_503_and_local_still_works(client, listener, jamendo_song, local_song):
    route = respx.get(JAMENDO_URL).mock(side_effect=httpx.ConnectTimeout("lento"))
    r = await stream(client, jamendo_song, listener)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "jamendo_unavailable"
    assert route.call_count == 2  # un reintento
    assert (await stream(client, local_song, listener, {"Range": "bytes=0-9"})).status_code == 206


@respx.mock
async def test_jamendo_error_status_503(client, listener, jamendo_song):
    respx.get(JAMENDO_URL).mock(return_value=httpx.Response(500))
    assert (await stream(client, jamendo_song, listener)).status_code == 503


async def test_redirect_mode_302(client, listener, jamendo_song, monkeypatch):
    monkeypatch.setattr(get_settings(), "JAMENDO_AUDIO_MODE", "redirect")
    r = await stream(client, jamendo_song, listener)
    assert r.status_code == 302
    assert r.headers["location"] == JAMENDO_URL


async def ticket_for(client, song, user):
    r = await client.post(f"/api/songs/{song.id}/stream-ticket", headers=user.headers)
    assert r.status_code == 200
    return r.json()


async def test_stream_with_ticket_no_header(client, listener, local_song):
    t = await ticket_for(client, local_song, listener)
    assert t["expires_in"] == 3600
    r = await client.get(f"/api/songs/{local_song.id}/stream?ticket={t['ticket']}")
    assert r.status_code == 200


async def test_stream_without_credentials_401(client, local_song):
    assert (await client.get(f"/api/songs/{local_song.id}/stream")).status_code == 401


async def test_ticket_only_for_its_song(client, listener, local_song, make_song):
    other = await make_song(title="Otra")
    t = await ticket_for(client, local_song, listener)
    assert (await client.get(f"/api/songs/{other.id}/stream?ticket={t['ticket']}")).status_code == 401


async def test_expired_ticket_401(client, listener, local_song):
    expired = create_token({"sub": listener.id, "scope": "stream", "song_id": str(local_song.id)}, -10)
    assert (await client.get(f"/api/songs/{local_song.id}/stream?ticket={expired}")).status_code == 401


async def test_ticket_is_not_a_session(client, listener, local_song):
    t = await ticket_for(client, local_song, listener)
    r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {t['ticket']}"})
    assert r.status_code == 401


async def test_access_token_not_accepted_as_ticket(client, listener, local_song):
    assert (await client.get(f"/api/songs/{local_song.id}/stream?ticket={listener.token}")).status_code == 401


async def test_suspended_user_ticket_rejected(client, admin, listener, local_song):
    t = await ticket_for(client, local_song, listener)
    await client.post(f"/api/admin/users/{listener.id}/suspend", json={}, headers=admin.headers)
    assert (await client.get(f"/api/songs/{local_song.id}/stream?ticket={t['ticket']}")).status_code == 401


async def test_hidden_song_not_streamable(client, listener, make_song):
    song = await make_song(status="hidden", audio_path="audio/x.mp3")
    assert (await stream(client, song, listener)).status_code == 404
    r = await client.post(f"/api/songs/{song.id}/stream-ticket", headers=listener.headers)
    assert r.status_code == 404




async def test_local_huge_range_start_416(client, listener, local_song):
    r = await stream(client, local_song, listener, {"Range": f"bytes={HUGE}-"})
    assert r.status_code == 416


@respx.mock
async def test_jamendo_416_passes_through_without_renewing(client, listener, jamendo_song):
    audio = respx.get(JAMENDO_URL).mock(return_value=httpx.Response(416))
    api = respx.get(url__startswith="https://api.jamendo.com/").mock(return_value=httpx.Response(500))
    r = await stream(client, jamendo_song, listener, {"Range": "bytes=999999-"})
    assert r.status_code == 416
    assert r.json()["error"]["code"] == "range_not_satisfiable"
    assert audio.call_count == 1
    assert api.call_count == 0


@respx.mock
async def test_jamendo_api_html_is_503(client, listener, jamendo_song):
    respx.get(JAMENDO_URL).mock(return_value=httpx.Response(403))
    respx.get(url__startswith="https://api.jamendo.com/").mock(
        return_value=httpx.Response(200, text="<html>mantenimiento</html>")
    )
    r = await stream(client, jamendo_song, listener)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "jamendo_unavailable"
