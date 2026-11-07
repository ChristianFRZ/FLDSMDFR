from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, current_user
from app.core.db import get_session
from app.modules.social import tapes
from app.modules.social.schemas import InviteIn, OrderIn, TapeIn, TapePatch, TrackIn

router = APIRouter(prefix="/api/tapes")

User = Depends(current_user)
Session = Depends(get_session)


@router.post("", status_code=201)
async def create(data: TapeIn, user: CurrentUser = User, session: AsyncSession = Session):
    tape = await tapes.create(session, user, data)
    return {"id": tape.id, "title": tape.title, "color": tape.color}


@router.get("")
async def mine(user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.list_mine(session, user)


# Las rutas fijas van antes que las de /{tape_id}.
@router.get("/invites/pending")
async def pending(user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.pending_invites(session, user)


@router.get("/invites/{token}")
async def preview(token: str, user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.preview(session, user, token)


@router.post("/invites/{token}/dismiss", status_code=204)
async def dismiss(token: str, user: CurrentUser = User, session: AsyncSession = Session):
    await tapes.dismiss_by_token(session, user, token)
    return Response(status_code=204)


@router.post("/join/{token}")
async def join(token: str, user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.join_by_token(session, user, token)


@router.post("/claims/{invite_id}/join")
async def join_claim(invite_id: UUID, user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.join_by_claim(session, user, invite_id)


@router.post("/claims/{invite_id}/dismiss", status_code=204)
async def dismiss_claim(invite_id: UUID, user: CurrentUser = User, session: AsyncSession = Session):
    await tapes.dismiss_by_claim(session, user, invite_id)
    return Response(status_code=204)


@router.get("/{tape_id}")
async def detail(tape_id: UUID, user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.detail(session, user, tape_id)


@router.patch("/{tape_id}")
async def update(tape_id: UUID, data: TapePatch, user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.update_tape(session, user, tape_id, data)


@router.delete("/{tape_id}", status_code=204)
async def delete(tape_id: UUID, user: CurrentUser = User, session: AsyncSession = Session):
    await tapes.delete_tape(session, user, tape_id)
    return Response(status_code=204)


@router.post("/{tape_id}/tracks", status_code=201)
async def add_track(tape_id: UUID, data: TrackIn, user: CurrentUser = User, session: AsyncSession = Session):
    track = await tapes.add_track(session, user, tape_id, data)
    return {"id": track.id, "position": track.position}


@router.delete("/{tape_id}/tracks/{track_id}", status_code=204)
async def remove_track(tape_id: UUID, track_id: UUID, user: CurrentUser = User, session: AsyncSession = Session):
    await tapes.remove_track(session, user, tape_id, track_id)
    return Response(status_code=204)


@router.put("/{tape_id}/order")
async def reorder(tape_id: UUID, data: OrderIn, user: CurrentUser = User, session: AsyncSession = Session):
    return {"version": await tapes.reorder(session, user, tape_id, data)}


@router.post("/{tape_id}/invites", status_code=201)
async def create_invite(tape_id: UUID, data: InviteIn, user: CurrentUser = User, session: AsyncSession = Session):
    return await tapes.create_invite(session, user, tape_id, data)


@router.delete("/{tape_id}/invites/{invite_id}", status_code=204)
async def revoke_invite(tape_id: UUID, invite_id: UUID, user: CurrentUser = User, session: AsyncSession = Session):
    await tapes.revoke_invite(session, user, tape_id, invite_id)
    return Response(status_code=204)
