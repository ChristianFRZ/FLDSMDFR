"""Casetes y vínculos ficticios de la semilla de demo."""
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete

from app.core.db import session_scope
from app.modules.catalog.public import get_songs
from app.modules.social.models import Favorite, Follow, NoticeSeen, Tape, TapeMember, TapeTrack
from app.modules.social.tapes import _cache


@dataclass(frozen=True)
class DemoTapeTrack:
    song_id: UUID
    added_by: UUID
    dedication: str | None


@dataclass(frozen=True)
class DemoTape:
    creator_id: UUID
    title: str
    color: str
    member_ids: list[UUID]
    tracks: list[DemoTapeTrack]


async def insert_demo_tapes(tapes: list[DemoTape]) -> None:
    songs = await get_songs(list({track.song_id for tape in tapes for track in tape.tracks}))
    async with session_scope() as session:
        for tape in tapes:
            row = Tape(title=tape.title, color=tape.color, creator_id=tape.creator_id, is_demo=True)
            session.add(row)
            await session.flush()
            session.add_all(TapeMember(tape_id=row.id, user_id=member) for member in tape.member_ids)
            session.add_all(
                TapeTrack(
                    tape_id=row.id,
                    song_id=track.song_id,
                    added_by=track.added_by,
                    position=position,
                    dedication=track.dedication,
                    metadata_cache=_cache(songs[track.song_id]),
                )
                for position, track in enumerate(tape.tracks, start=1)
            )


async def insert_demo_links(favorites: list[tuple[UUID, UUID]], follows: list[tuple[UUID, UUID]]) -> None:
    async with session_scope() as session:
        session.add_all(Favorite(user_id=user, song_id=song) for user, song in favorites)
        session.add_all(Follow(user_id=user, artist_id=artist) for user, artist in follows)


async def clear_demo_social(user_ids: list[UUID]) -> None:
    async with session_scope() as session:
        await session.execute(delete(Tape).where(Tape.is_demo.is_(True)))
        for model in (Favorite, Follow, NoticeSeen):
            await session.execute(delete(model).where(model.user_id.in_(user_ids)))
