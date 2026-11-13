from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from meloxo_common.auth import CurrentUser
from meloxo_common.errors import AppError
from meloxo_common.pagination import PageParams, page_body
from meloxo_common.internal import UpstreamError

from playback_metrics.clients.catalog import get_songs
from playback_metrics.modules.playback.models import Playback, PlaybackCounter
from playback_metrics.modules.playback.schemas import PlaybackIn

DUPLICATES = "duplicates_discarded"


async def record(session: AsyncSession, user: CurrentUser, data: PlaybackIn) -> bool:
    """Devuelve True si es una reproducción nueva, False si era un reenvío."""
    try:
        known = data.song_id in await get_songs([data.song_id])
    except UpstreamError:
        known = True  # Con catálogo caído se guarda igual: perder una reproducción es peor que aceptar un id sin validar.
    if not known:
        raise AppError(404, "song_not_found", "Canción no encontrada")
    statement = (
        insert(Playback)
        .values(
            playback_id=data.playback_id,
            user_id=user.id,
            song_id=data.song_id,
            listened_seconds=data.listened_seconds,
        )
        .on_conflict_do_nothing(index_elements=[Playback.playback_id])
        .returning(Playback.seq)
    )
    created = (await session.execute(statement)).first() is not None
    if not created:
        counter = insert(PlaybackCounter).values(key=DUPLICATES, value=1)
        await session.execute(
            counter.on_conflict_do_update(
                index_elements=[PlaybackCounter.key], set_={"value": PlaybackCounter.value + 1}
            )
        )
    await session.commit()
    return created


async def progress(session: AsyncSession, user: CurrentUser, playback_id: UUID, seconds: int) -> int:
    owner = await session.scalar(select(Playback.user_id).where(Playback.playback_id == playback_id))
    if owner is None:
        raise AppError(404, "playback_not_found", "Reproducción no encontrada")
    if owner != user.id:
        raise AppError(403, "forbidden", "Esta reproducción no es tuya")
    statement = (
        update(Playback)
        .where(Playback.playback_id == playback_id)
        .values(listened_seconds=func.greatest(Playback.listened_seconds, seconds))
        .returning(Playback.listened_seconds)
    )
    listened = await session.scalar(statement)
    await session.commit()
    return listened


async def history(session: AsyncSession, user: CurrentUser, params: PageParams) -> dict:
    mine = Playback.user_id == user.id
    total = await session.scalar(select(func.count()).select_from(Playback).where(mine))
    query = (
        select(Playback)
        .where(mine)
        .order_by(Playback.seq.desc())
        .limit(params.size)
        .offset((params.page - 1) * params.size)
    )
    rows = list((await session.execute(query)).scalars())
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    songs = await get_songs(list({r.song_id for r in rows}))
    items = [
        {
            "playback_id": r.playback_id,
            "listened_seconds": r.listened_seconds,
            "started_at": r.started_at,
            "song": songs.get(r.song_id),
        }
        for r in rows
    ]
    return page_body(items, total, params)
