"""catalog-streaming simulado con respx: las mismas rutas `/internal/*` que expone el servicio real."""
import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx

CATALOG_URL = "http://catalog.test"


def _summary(song: SimpleNamespace) -> dict:
    return {
        "id": str(song.id),
        "title": song.title,
        "artist_id": str(song.artist_id),
        "artist": song.artist,
        "album": song.album,
        "duration": song.duration,
        "cover_url": None,
        "source": song.source,
        "license": song.license,
        "license_url": None,
        "jamendo_url": None,
        "genres": list(song.genres),
        "status": song.status,
        "available": song.status == "published",
    }


class FakeCatalog:
    def __init__(self, router):
        self.songs: dict[UUID, SimpleNamespace] = {}
        self.artists: dict[str, SimpleNamespace] = {}
        self.calls: list[httpx.Request] = []
        self.down = False
        self.delay = 0.0
        router.get(f"{CATALOG_URL}/internal/songs", name="cat_songs").mock(side_effect=self._songs)
        router.get(f"{CATALOG_URL}/internal/artists", name="cat_artists").mock(side_effect=self._artists)
        router.get(url__regex=rf"{CATALOG_URL}/internal/songs/(?P<song_id>[^/]+)/playable", name="cat_playable").mock(
            side_effect=self._playable
        )
        router.get(f"{CATALOG_URL}/internal/artists/upcoming", name="cat_upcoming").mock(side_effect=self._upcoming)
        router.get(f"{CATALOG_URL}/internal/artists/published-since", name="cat_published").mock(
            side_effect=self._published
        )
        router.get(url__regex=rf"{CATALOG_URL}/internal/owners/(?P<user_id>[^/]+)/songs", name="cat_owned").mock(
            side_effect=self._owned
        )

    # Lo que hacen las pruebas para preparar el catálogo

    def add_song(
        self,
        title="Luz de carretera",
        artist="Marea Baja",
        album="Noches",
        source="local",
        status="published",
        genres=("rock",),
        owner=None,
        duration=180,
        publish_at=None,
        published_at=None,
        license="CC BY-NC-SA",
        **_,
    ) -> SimpleNamespace:
        found = self.artists.get(artist)
        if found is None:
            found = SimpleNamespace(id=uuid4(), name=artist, source=source, owner=owner)
            self.artists[artist] = found
        if status == "published" and published_at is None and source == "local":
            published_at = datetime.now(UTC)
        song = SimpleNamespace(
            id=uuid4(), title=title, artist_id=found.id, artist=artist, album=album, duration=duration,
            source=source, license=license, genres=tuple(genres), status=status, owner=found.owner,
            publish_at=publish_at, published_at=published_at,
        )  # fmt: skip
        self.songs[song.id] = song
        return song

    def hide(self, song) -> None:
        self.songs[song.id].status = "hidden"

    def delete(self, song) -> None:
        del self.songs[song.id]

    # Rutas

    async def _gate(self, request: httpx.Request) -> None:
        self.calls.append(request)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.down:
            raise httpx.ConnectError("catálogo caído")

    @staticmethod
    def _ids(request: httpx.Request, key: str) -> list[UUID]:
        return [UUID(part) for part in request.url.params.get(key, "").split(",") if part]

    async def _songs(self, request):
        await self._gate(request)
        ids = self._ids(request, "ids")
        return httpx.Response(200, json={str(i): _summary(self.songs[i]) for i in ids if i in self.songs})

    async def _artists(self, request):
        await self._gate(request)
        by_id = {a.id: a for a in self.artists.values()}
        found = {
            str(i): {"id": str(i), "name": by_id[i].name, "source": by_id[i].source, "bio": "", "photo_url": None, "links": {}}
            for i in self._ids(request, "ids")
            if i in by_id
        }
        return httpx.Response(200, json=found)

    async def _playable(self, request, song_id):
        await self._gate(request)
        song = self.songs.get(UUID(song_id))
        return httpx.Response(200, json={"playable": song is not None and song.status == "published"})

    async def _upcoming(self, request):
        await self._gate(request)
        ids = set(self._ids(request, "artist_ids"))
        rows = sorted(
            (s for s in self.songs.values() if s.artist_id in ids and s.status == "scheduled" and s.publish_at),
            key=lambda s: s.publish_at,
        )
        return httpx.Response(
            200,
            json=[
                {"song_id": str(s.id), "title": s.title, "artist_id": str(s.artist_id), "artist": s.artist,
                 "publish_at": s.publish_at.isoformat()}
                for s in rows
            ],
        )  # fmt: skip

    async def _published(self, request):
        await self._gate(request)
        ids = set(self._ids(request, "artist_ids"))
        raw = request.url.params.get("since", "")
        since = datetime.fromisoformat(raw) if raw else None
        rows = sorted(
            (
                s for s in self.songs.values()
                if s.artist_id in ids and s.status == "published" and s.source == "local"
                and (since is None or s.published_at > since)
            ),
            key=lambda s: s.published_at,
            reverse=True,
        )[:50]  # fmt: skip
        return httpx.Response(
            200, json=[{"song": _summary(s), "published_at": s.published_at.isoformat()} for s in rows]
        )

    async def _owned(self, request, user_id):
        await self._gate(request)
        return httpx.Response(200, json=[str(s.id) for s in self.songs.values() if str(s.owner) == user_id])
