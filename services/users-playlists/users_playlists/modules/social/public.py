"""Interfaz pública de modules.social. Solo tipos simples; cada función abre su sesión."""
from uuid import UUID

from sqlalchemy import func, select

from meloxo_common.db import session_scope
from users_playlists.modules.social.models import Tape, TapeMember, TapeTrack
from users_playlists.modules.social.release_consumer import run_release_consumer
from users_playlists.modules.social.schemas import TapeActivity
from users_playlists.modules.social.demo import DemoTape, DemoTapeTrack, clear_demo_social, insert_demo_links, insert_demo_tapes  # noqa: F401

__all__ = ["TapeActivity", "run_release_consumer", "count_tape_inclusions", "tape_activity", "DemoTape", "DemoTapeTrack", "clear_demo_social", "insert_demo_links", "insert_demo_tapes"]


async def count_tape_inclusions(song_ids: list[UUID]) -> int:
    """Cuántos casetes incluyen alguna de estas pistas. Solo un conteo, sin identidades."""
    if not song_ids:
        return 0
    query = select(func.count(func.distinct(TapeTrack.tape_id))).where(TapeTrack.song_id.in_(song_ids))
    async with session_scope() as session:
        return await session.scalar(query) or 0


async def tape_activity() -> TapeActivity:
    async with session_scope() as session:
        tapes = await session.scalar(select(func.count()).select_from(Tape))
        members = await session.scalar(select(func.count()).select_from(TapeMember))
        tracks = await session.scalar(select(func.count()).select_from(TapeTrack))
        dedications = await session.scalar(
            select(func.count()).select_from(TapeTrack).where(TapeTrack.dedication.is_not(None))
        )
    return TapeActivity(tapes=tapes, members=members, tracks=tracks, dedications=dedications)
