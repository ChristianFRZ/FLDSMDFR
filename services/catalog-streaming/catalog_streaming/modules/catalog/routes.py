from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from meloxo_common.auth import CurrentUser
from meloxo_common.db import get_session
from meloxo_common.errors import AppError
from meloxo_common.pagination import PageParams, page_body, page_params
from meloxo_common.contracts import AuditEntry
from meloxo_common.internal import UpstreamError
from meloxo_common.security import decode_token, encode_token

from catalog_streaming.auth import auth, auth_state_cache
from catalog_streaming.modules.catalog import import_jobs, publishing, service, streaming
from catalog_streaming.modules.catalog.schemas import HideIn, ImportIn, ImportJobOut
from catalog_streaming.clients.users import record_audit

router = APIRouter(prefix="/api")
_bearer = HTTPBearer(auto_error=False)
TICKET_SECONDS = 3600
current_user = auth.current_user
is_admin = auth.require_role("admin")


@router.get("/songs")
async def songs(
    q: str | None = None,
    genre: str | None = None,
    artist: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    params: PageParams = Depends(page_params),
    _: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    items, total = await service.search_songs(session, params, q, genre, artist, tag, source)
    return page_body(items, total, params)


@router.get("/songs/{song_id}")
async def song(song_id: UUID, _: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return service.to_summary(await service.get_published_song(session, song_id))


@router.get("/artists/{artist_id}")
async def artist(artist_id: UUID, _: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.artist_page(session, artist_id)


@router.get("/genres")
async def genres(_: CurrentUser = Depends(current_user), session: AsyncSession = Depends(get_session)):
    return await service.list_genres(session)


@router.post("/songs/{song_id}/stream-ticket")
async def stream_ticket(song_id: UUID, user: CurrentUser = Depends(current_user)):
    """El elemento <audio> no puede enviar Authorization: usa un ticket corto ligado a la pista."""
    await streaming.load_target(song_id)
    ticket = encode_token(
        {"sub": str(user.id), "scope": "stream", "song_id": str(song_id)}, timedelta(seconds=TICKET_SECONDS)
    )
    return {"ticket": ticket, "expires_in": TICKET_SECONDS}


async def _authorize_stream(song_id: UUID, ticket: str | None, bearer: HTTPAuthorizationCredentials | None) -> None:
    invalid = AppError(401, "invalid_ticket", "El permiso de reproducción venció")
    if ticket is None:
        if bearer is None:
            raise AppError(401, "not_authenticated", "Inicia sesión para continuar")
        await auth.resolve_user(bearer.credentials)
        return
    claims = decode_token(ticket)
    if claims.get("scope") != "stream" or claims.get("song_id") != str(song_id):
        raise invalid
    try:
        state = await auth_state_cache.get(UUID(claims["sub"]))
    except UpstreamError:
        return  # el ticket va firmado: sin users-playlists y sin estado guardado sigue valiendo
    if state is None or state.status != "active":
        raise invalid


@router.get("/songs/{song_id}/stream")
async def stream(
    song_id: UUID,
    ticket: str | None = Query(default=None),
    range_header: str | None = Header(default=None, alias="Range"),
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    await _authorize_stream(song_id, ticket, bearer)
    return await streaming.stream_song(song_id, range_header)


@router.post("/admin/catalog/import", status_code=202)
async def start_import(data: ImportIn, user: CurrentUser = Depends(is_admin)):
    params = data.model_dump()

    async def audit(job_id: UUID) -> None:
        entry = AuditEntry(
            actor_id=user.id, action="catalog_import", target_type="import_job", target_id=str(job_id), detail=params
        )
        await record_audit(entry)

    job_id = await import_jobs.create_job(user.id, params, before_commit=audit)
    import_jobs.spawn(import_jobs.run_import_job(job_id))
    return {"job_id": job_id}


@router.get("/admin/catalog/import", response_model=list[ImportJobOut])
async def list_imports(_: CurrentUser = Depends(is_admin)):
    return await import_jobs.list_jobs()


@router.get("/admin/catalog/import/{job_id}", response_model=ImportJobOut)
async def import_status(job_id: UUID, _: CurrentUser = Depends(is_admin)):
    return await import_jobs.get_job(job_id)


@router.post("/admin/catalog/import/{job_id}/resume", response_model=ImportJobOut, status_code=202)
async def resume_import(job_id: UUID, _: CurrentUser = Depends(is_admin)):
    return await import_jobs.resume_job(job_id)


@router.get("/admin/songs")
async def admin_songs(
    q: str | None = None,
    status: str | None = None,
    source: str | None = None,
    params: PageParams = Depends(page_params),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    items, total = await publishing.list_all_songs(session, params, q, status, source)
    return page_body(items, total, params)


@router.post("/admin/songs/{song_id}/hide")
async def hide_song(
    song_id: UUID,
    data: HideIn,
    user: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return await publishing.hide_song(session, user.id, song_id, data.reason)


@router.post("/admin/songs/{song_id}/restore")
async def restore_song(
    song_id: UUID, user: CurrentUser = Depends(is_admin), session: AsyncSession = Depends(get_session)
):
    return await publishing.restore_song(session, user.id, song_id)
