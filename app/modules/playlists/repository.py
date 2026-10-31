import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.playlists.models import Playlist, PlaylistSong


async def get_owned(
    session: AsyncSession,
    owner_id: uuid.UUID,
    playlist_id: uuid.UUID,
    for_update: bool = False,
):
    """`for_update` bloquea la fila del casete: serializa las mutaciones concurrentes."""
    stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.owner_id == owner_id)
    if for_update:
        stmt = stmt.with_for_update()
    return await session.scalar(stmt)


async def add(session: AsyncSession, playlist: Playlist) -> Playlist:
    session.add(playlist)
    await session.commit()
    return playlist


async def list_with_counts(
    session: AsyncSession, owner_id: uuid.UUID
) -> list[tuple[Playlist, int]]:
    count = func.count(PlaylistSong.song_id)
    stmt = (
        select(Playlist, count)
        .outerjoin(PlaylistSong, PlaylistSong.playlist_id == Playlist.id)
        .where(Playlist.owner_id == owner_id)
        .group_by(Playlist.id)
        .order_by(Playlist.created_at, Playlist.id)
    )
    return [(p, n) for p, n in (await session.execute(stmt)).all()]


async def count_songs(session: AsyncSession, playlist_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(PlaylistSong)
        .where(PlaylistSong.playlist_id == playlist_id)
    )
    return await session.scalar(stmt) or 0


async def list_songs(session: AsyncSession, playlist_id: uuid.UUID) -> list[PlaylistSong]:
    stmt = (
        select(PlaylistSong)
        .where(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position)
    )
    return list((await session.scalars(stmt)).all())


async def max_position(session: AsyncSession, playlist_id: uuid.UUID) -> int:
    stmt = select(func.max(PlaylistSong.position)).where(PlaylistSong.playlist_id == playlist_id)
    return await session.scalar(stmt) or 0


async def get_entry(
    session: AsyncSession, playlist_id: uuid.UUID, song_id: uuid.UUID
) -> PlaylistSong | None:
    return await session.get(PlaylistSong, (playlist_id, song_id))


async def delete_playlist(session: AsyncSession, playlist: Playlist) -> None:
    await session.delete(playlist)
    await session.commit()


async def delete_entry(session: AsyncSession, entry: PlaylistSong) -> None:
    await session.execute(
        delete(PlaylistSong).where(
            PlaylistSong.playlist_id == entry.playlist_id, PlaylistSong.song_id == entry.song_id
        )
    )


def touch(playlist: Playlist) -> None:
    playlist.updated_at = datetime.now(UTC)
