"""Rutas `/internal/*`: envoltorio fino sobre `modules/*/public.py`.

nginx no las publica y no llevan autenticación: solo las llaman otros servicios dentro de la red de Docker.
"""
import dataclasses
import time
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from sqlalchemy import text

from meloxo_common.contracts import AuditEntry, AuthState, TapeActivity, UserGrowthPoint
from meloxo_common.db import session_scope
from meloxo_common.errors import AppError

from users_playlists.modules.playlists import public as playlists
from users_playlists.modules.social import public as social
from users_playlists.modules.users import public as users

MAX_IDS = 200
router = APIRouter(prefix="/internal")
_started = time.monotonic()


def _parse(raw: str, field: str) -> list[UUID]:
    """Lista separada por comas; vacía es válida. Más de 200 o un id mal formado dan 422."""
    try:
        ids = [UUID(part) for part in raw.split(",") if part]
    except ValueError:
        raise RequestValidationError([{"loc": ("query", field), "msg": "Identificador no válido", "type": "value_error"}])
    if len(ids) > MAX_IDS:
        raise RequestValidationError(
            [{"loc": ("query", field), "msg": f"Máximo {MAX_IDS} identificadores", "type": "value_error"}]
        )
    return ids


@router.get("/users/display-names")
async def display_names(ids: str = "") -> dict[UUID, str]:
    return await users.get_display_names(_parse(ids, "ids"))


@router.get("/users/growth")
async def growth(days: int = 30) -> list[UserGrowthPoint]:
    return [UserGrowthPoint(**dataclasses.asdict(p)) for p in await users.user_growth(days)]


@router.get("/users/{user_id}/auth-state")
async def auth_state(user_id: UUID) -> AuthState:
    state = await users.get_auth_state(user_id)
    if state is None:
        raise AppError(404, "not_found", "Usuario no encontrado")
    return AuthState(**dataclasses.asdict(state))


@router.post("/audit", status_code=204)
async def audit(entry: AuditEntry) -> None:
    await users.record_audit(
        entry.actor_id, entry.action, entry.target_type, entry.target_id, entry.detail, entry.outcome
    )


@router.get("/playlists/inclusions")
async def playlist_inclusions(song_ids: str = "") -> dict[str, int]:
    return {"count": await playlists.count_inclusions(_parse(song_ids, "song_ids"))}


@router.get("/tapes/inclusions")
async def tape_inclusions(song_ids: str = "") -> dict[str, int]:
    return {"count": await social.count_tape_inclusions(_parse(song_ids, "song_ids"))}


@router.get("/tapes/activity")
async def tape_activity() -> TapeActivity:
    return TapeActivity(**dataclasses.asdict(await social.tape_activity()))


@router.get("/health")
async def health() -> dict:
    """Siempre 200: si la base no responde, `status` es `down` y `database_ms` es 0."""
    start = time.perf_counter()
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
        status, database_ms = "up", (time.perf_counter() - start) * 1000
    except Exception:
        status, database_ms = "down", 0.0
    return {
        "name": "users-playlists",
        "status": status,
        "database_ms": float(database_ms),
        "uptime_seconds": int(time.monotonic() - _started),
    }


class DemoUserIn(BaseModel):
    email: str
    display_name: str
    role: str
    created_at: datetime
    request_message: str | None = None


class DemoUsersIn(BaseModel):
    users: list[DemoUserIn]
    password: str


class DemoUsersOut(BaseModel):
    ids: dict[str, UUID]


class DemoPlaylistIn(BaseModel):
    owner_id: UUID
    name: str
    is_public: bool
    song_ids: list[UUID]


class DemoPlaylistsIn(BaseModel):
    playlists: list[DemoPlaylistIn]


class DemoTapeTrackIn(BaseModel):
    song_id: UUID
    added_by: UUID
    dedication: str | None = None


class DemoTapeIn(BaseModel):
    creator_id: UUID
    title: str
    color: str
    member_ids: list[UUID]
    tracks: list[DemoTapeTrackIn]


class DemoSocialIn(BaseModel):
    tapes: list[DemoTapeIn] = []
    favorites: list[tuple[UUID, UUID]] = []  # (user_id, song_id)
    follows: list[tuple[UUID, UUID]] = []  # (user_id, artist_id)


class DemoSocialClearIn(BaseModel):
    user_ids: list[UUID]


@router.post("/demo/users")
async def insert_demo_users(body: DemoUsersIn) -> DemoUsersOut:
    ids = await users.insert_demo_users([users.DemoUser(**u.model_dump()) for u in body.users], body.password)
    return DemoUsersOut(ids=ids)


@router.get("/demo/users/ids")
async def demo_user_ids() -> dict[str, list[UUID]]:
    return {"ids": await users.demo_user_ids()}


@router.post("/demo/users/clear", status_code=204)
async def clear_demo_users() -> None:
    await users.clear_demo_users()


@router.post("/demo/playlists", status_code=204)
async def insert_demo_playlists(body: DemoPlaylistsIn) -> None:
    await playlists.insert_demo_playlists([playlists.DemoPlaylist(**p.model_dump()) for p in body.playlists])


@router.post("/demo/playlists/clear", status_code=204)
async def clear_demo_playlists() -> None:
    await playlists.clear_demo_playlists()


@router.post("/demo/social", status_code=204)
async def insert_demo_social(body: DemoSocialIn) -> None:
    tapes = [
        social.DemoTape(
            t.creator_id, t.title, t.color, t.member_ids, [social.DemoTapeTrack(**x.model_dump()) for x in t.tracks]
        )
        for t in body.tapes
    ]
    await social.insert_demo_tapes(tapes)
    await social.insert_demo_links(body.favorites, body.follows)


@router.post("/demo/social/clear", status_code=204)
async def clear_demo_social(body: DemoSocialClearIn) -> None:
    await social.clear_demo_social(body.user_ids)
