"""Playlists ficticias de la semilla de demo."""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete

from app.core.db import session_scope
from app.modules.catalog.public import get_songs
from app.modules.playlists.models import Playlist, PlaylistSong
from app.modules.playlists.service import _cache


@dataclass(frozen=True)
class DemoPlaylist:
    owner_id: UUID
    name: str
    is_public: bool
    song_ids: list[UUID]


async def insert_demo_playlists(playlists: list[DemoPlaylist]) -> None:
    songs = await get_songs(list({song_id for playlist in playlists for song_id in playlist.song_ids}))
    async with session_scope() as session:
        for playlist in playlists:
            row = Playlist(owner_id=playlist.owner_id, name=playlist.name, is_public=playlist.is_public, is_demo=True)
            session.add(row)
            await session.flush()
            session.add_all(
                PlaylistSong(playlist_id=row.id, song_id=song_id, position=position, metadata_cache=_cache(songs[song_id]))
                for position, song_id in enumerate(playlist.song_ids, start=1)
            )


async def clear_demo_playlists() -> None:
    async with session_scope() as session:
        await session.execute(delete(Playlist).where(Playlist.is_demo.is_(True)))
