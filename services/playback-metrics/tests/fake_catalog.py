"""Catálogo falso en memoria con el mismo contrato /internal que catalog-streaming.

Sustituye al servicio real en las pruebas de playback-metrics: se instala como transporte
ASGI del cliente HTTP, así que el código bajo prueba hace peticiones de verdad.
"""

import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.clients.catalog_schemas import SongOut


def _key(name: str) -> str:
    return name.strip().lower()


class _Ids(BaseModel):
    ids: list[uuid.UUID]


class _Artists(BaseModel):
    artists: list[str]


class _Follow(BaseModel):
    artist: str
    since: datetime


class _Releases(BaseModel):
    follows: list[_Follow]
    not_before: datetime


def _not_found() -> JSONResponse:
    return JSONResponse(
        {"error": {"code": "song_not_found", "message": "La canción no existe."}},
        status_code=404,
    )


class FakeCatalog:
    current: "FakeCatalog"  # el instalado por la fixture `catalog`

    def __init__(self) -> None:
        self.songs: dict[uuid.UUID, SongOut] = {}
        self.app = self._build()

    def add_song(
        self,
        title: str = "Nubes de agosto",
        artist: str = "Los Meteoros",
        album: str = "Pronóstico",
        duration_seconds: int = 2,
        created_at: datetime | None = None,
    ) -> SongOut:
        song = SongOut(
            id=uuid.uuid4(),
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
            is_active=True,
            created_at=created_at or datetime.now(UTC),
        )
        self.songs[song.id] = song
        return song

    def deactivate(self, song_id: uuid.UUID) -> None:
        self.songs[song_id] = self.songs[song_id].model_copy(update={"is_active": False})

    def _active(self) -> list[SongOut]:
        return [s for s in self.songs.values() if s.is_active]

    def _build(self) -> FastAPI:
        app = FastAPI()

        @app.get("/internal/songs/count")
        async def count():
            return {"count": len(self._active())}

        @app.get("/internal/songs/lookup")
        async def lookup(title: str = Query(), artist: str = Query()):
            for s in self.songs.values():
                if _key(s.title) == _key(title) and _key(s.artist) == _key(artist):
                    return s
            return _not_found()

        @app.get("/internal/songs/{song_id}")
        async def get_song(song_id: uuid.UUID):
            song = self.songs.get(song_id)
            return song if song is not None and song.is_active else _not_found()

        @app.post("/internal/songs/batch")
        async def batch(data: _Ids):
            return [self.songs[i] for i in data.ids if i in self.songs]

        @app.post("/internal/artists/counts")
        async def counts(data: _Artists):
            keys = {_key(a) for a in data.artists}
            out: dict[str, int] = {}
            for s in self._active():
                if _key(s.artist) in keys:
                    out[_key(s.artist)] = out.get(_key(s.artist), 0) + 1
            return out

        @app.post("/internal/artists/latest")
        async def latest(data: _Artists):
            keys = {_key(a) for a in data.artists}
            out: dict[str, SongOut] = {}
            for s in sorted(self._active(), key=lambda s: s.created_at):
                if _key(s.artist) in keys:
                    out[_key(s.artist)] = s
            return out

        @app.post("/internal/artists/releases")
        async def releases(data: _Releases):
            windows = {_key(f.artist): max(f.since, data.not_before) for f in data.follows}
            found = [
                s
                for s in self._active()
                if _key(s.artist) in windows and s.created_at > windows[_key(s.artist)]
            ]
            return sorted(found, key=lambda s: s.created_at, reverse=True)[:50]

        return app
