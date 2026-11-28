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
        self.router = router
        self.songs: dict[UUID, SimpleNamespace] = {}
        self.artists: dict[str, SimpleNamespace] = {}
        self.calls: list[httpx.Request] = []
        self.down = False
        self.delay = 0.0
        self.jamendo = "up"
        self.health_error: Exception | None = None
        self.buckets: list[dict] = []
        router.get(f"{CATALOG_URL}/internal/health", name="cat_health").mock(side_effect=self._health)
        router.post(f"{CATALOG_URL}/internal/latency/drain", name="cat_drain").mock(side_effect=self._drain)
        router.get(f"{CATALOG_URL}/internal/songs", name="cat_songs").mock(side_effect=self._songs)
        router.get(f"{CATALOG_URL}/internal/artists", name="cat_artists").mock(side_effect=self._artists)
        router.get(f"{CATALOG_URL}/internal/catalog/by-source", name="cat_by_source").mock(side_effect=self._by_source)
        router.get(f"{CATALOG_URL}/internal/catalog/release-counts", name="cat_releases").mock(side_effect=self._releases)
        router.get(f"{CATALOG_URL}/internal/jamendo-status", name="cat_jamendo").mock(side_effect=self._jamendo)
        router.get(url__regex=rf"{CATALOG_URL}/internal/owners/(?P<user_id>[^/]+)/songs", name="cat_owned").mock(
            side_effect=self._owned
        )

    def add_replica(self, address: str) -> "ReplicaDrain":
        """Una réplica con su propia dirección y sus propios buckets, para `/internal/latency/drain`."""
        replica = ReplicaDrain(self, address)
        self.router.post(f"{address}/internal/latency/drain").mock(side_effect=replica.drain)
        return replica

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

    async def _by_source(self, request):
        await self._gate(request)
        counts: dict[str, int] = {}
        for song in self.songs.values():
            counts[song.source] = counts.get(song.source, 0) + 1
        return httpx.Response(200, json=counts)

    async def _releases(self, request):
        await self._gate(request)
        owner = request.url.params.get("owner_id")
        rows = [s for s in self.songs.values() if owner is None or str(s.owner) == owner]
        return httpx.Response(
            200,
            json={
                "scheduled": sum(s.status == "scheduled" for s in rows),
                "published": sum(s.status == "published" for s in rows),
            },
        )

    async def _jamendo(self, request):
        await self._gate(request)
        return httpx.Response(200, json={"status": self.jamendo})

    async def _owned(self, request, user_id):
        await self._gate(request)
        return httpx.Response(200, json=[str(s.id) for s in self.songs.values() if str(s.owner) == user_id])

    async def _health(self, request):
        await self._gate(request)
        if self.health_error:
            raise self.health_error
        return httpx.Response(
            200, json={"name": "catalog-streaming", "status": "up", "database_ms": 2.5, "uptime_seconds": 90}
        )

    async def _drain(self, request):
        await self._gate(request)
        taken, self.buckets = self.buckets, []
        return httpx.Response(200, json=taken)


class ReplicaDrain:
    """Una réplica de catálogo que solo atiende el drenaje de latencia."""

    def __init__(self, catalog: FakeCatalog, address: str):
        self.catalog = catalog
        self.address = address
        self.buckets: list[dict] = []
        self.error: Exception | None = None

    async def drain(self, request):
        self.catalog.calls.append(request)
        if self.error:
            raise self.error
        taken, self.buckets = self.buckets, []
        return httpx.Response(200, json=taken)
