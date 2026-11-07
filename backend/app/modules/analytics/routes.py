import csv
import dataclasses
import io
import time
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, current_user, require_role
from app.core.db import get_session
from app.core.errors import AppError
from app.modules.analytics import service
from app.modules.analytics.aggregates import lag_seconds
from app.modules.catalog.public import (
    catalog_by_source,
    get_songs,
    jamendo_status,
    release_counts,
    songs_owned_by,
)
from app.modules.playback.public import duplicates_discarded, recent_activity, retention_for_songs
from app.modules.playlists.public import count_inclusions
from app.modules.social.public import count_tape_inclusions, tape_activity
from app.modules.users.public import user_growth

router = APIRouter(prefix="/api")

is_admin = require_role("admin")
is_composer = require_role("composer")

Days = Query(30, ge=1, le=366)
MAX_LAG_SECONDS = 30
ACTIVITY_MINUTES = 30


def _forbidden() -> AppError:
    return AppError(403, "forbidden", "No tienes acceso a estos datos")


def _time_zone(tz: str = Query("UTC", max_length=64)) -> str:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AppError(422, "invalid_timezone", "Zona horaria desconocida") from exc
    return tz


def _personal(scope: str, user: CurrentUser) -> UUID | None:
    """`me` limita a los datos de quien pregunta; `global` es solo de administración."""
    if scope == "me":
        return user.id
    if user.role != "admin":
        raise _forbidden()
    return None


@router.get("/metrics/top")
async def top(
    scope: Literal["global", "me"] = "global",
    kind: Literal["songs", "artists"] = "songs",
    limit: int = Query(10, ge=1, le=50),
    days: int = Days,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return {"items": await service.top(session, kind, limit, days, _personal(scope, user))}


@router.get("/metrics/genres")
async def genres(
    scope: Literal["global", "me"] = "global",
    days: int = Days,
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    return {"items": await service.genres(session, days, _personal(scope, user))}


@router.get("/metrics/plays")
async def plays(
    scope: Literal["global", "composer"] = "global",
    group: Literal["day", "hour"] = "day",
    days: int = Days,
    tz: str = Depends(_time_zone),
    user: CurrentUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    if (scope == "global" and user.role != "admin") or (scope == "composer" and user.role != "composer"):
        raise _forbidden()
    song_ids = await songs_owned_by(user.id) if scope == "composer" else None
    return {"items": await service.plays(session, group, days, tz, song_ids)}


@router.get("/metrics/heatmap")
async def heatmap(
    days: int = Days,
    tz: str = Depends(_time_zone),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return {"items": await service.heatmap(session, days, tz)}


@router.get("/metrics/catalog-sources")
async def catalog_sources(_: CurrentUser = Depends(is_admin)):
    counts = await catalog_by_source()
    return {"items": [{"source": source, "count": count} for source, count in sorted(counts.items())]}


@router.get("/metrics/user-growth")
async def growth(days: int = Days, _: CurrentUser = Depends(is_admin)):
    return {"items": [dataclasses.asdict(point) for point in await user_growth(days)]}


@router.get("/metrics/retention")
async def retention(user: CurrentUser = Depends(is_composer)):
    songs = await get_songs(await songs_owned_by(user.id))
    items = []
    for song in songs.values():
        stats = await retention_for_songs([song.id], {song.id: song.duration or 0})
        items.append({"song_id": song.id, "title": song.title, **dataclasses.asdict(stats)})
    return {"items": items}


@router.get("/metrics/tape-activity")
async def activity(_: CurrentUser = Depends(is_admin)):
    return dataclasses.asdict(await tape_activity())


@router.get("/metrics/releases")
async def releases(
    scope: Literal["global", "composer"] = "global",
    user: CurrentUser = Depends(current_user),
):
    if (scope == "global" and user.role != "admin") or (scope == "composer" and user.role != "composer"):
        raise _forbidden()
    return dataclasses.asdict(await release_counts(user.id if scope == "composer" else None))


@router.get("/metrics/latency")
async def latency(
    minutes: int = Query(60, ge=1, le=1440),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    return {"items": await service.latency(session, minutes)}


@router.get("/metrics/duplicates")
async def duplicates(_: CurrentUser = Depends(is_admin)):
    return {"duplicates_discarded": await duplicates_discarded()}


@router.get("/metrics/inclusions")
async def inclusions(user: CurrentUser = Depends(is_composer)):
    song_ids = await songs_owned_by(user.id)
    return {"playlists": await count_inclusions(song_ids), "tapes": await count_tape_inclusions(song_ids)}


@router.get("/admin/health")
async def health(_: CurrentUser = Depends(is_admin), session: AsyncSession = Depends(get_session)):
    database = {"name": "database", "status": "down"}
    try:
        started = time.perf_counter()
        await session.execute(text("SELECT 1"))
        await session.commit()
        database = {"name": "database", "status": "up", "ms": round((time.perf_counter() - started) * 1000, 1)}
    except Exception:
        pass
    aggregates = {"name": "aggregates", "status": "down"}
    if database["status"] == "up":
        lag = await lag_seconds()
        aggregates = {
            "name": "aggregates",
            "status": "up" if lag is None or lag < MAX_LAG_SECONDS else "delayed",
            "lag_seconds": lag,
        }
    app = {"name": "app", "status": "up", "uptime_seconds": service.uptime_seconds()}
    return {"services": [app, database, {"name": "jamendo", "status": await jamendo_status()}, aggregates]}


@router.get("/admin/health/system")
async def health_system(_: CurrentUser = Depends(is_admin), session: AsyncSession = Depends(get_session)):
    return await service.system_status(session)


@router.get("/admin/health/activity")
async def health_activity(_: CurrentUser = Depends(is_admin)):
    listeners, plays = await recent_activity(ACTIVITY_MINUTES)
    return {"minutes": ACTIVITY_MINUTES, "listeners": listeners, "plays": plays}


def _safe_cell(value: object) -> object:
    """Un título que empieza con = o @ se ejecutaría como fórmula al abrir el CSV en una hoja de cálculo."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{value}"
    return value


def _to_csv(rows: list[dict]) -> str:
    out = io.StringIO()
    if rows:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: _safe_cell(value) for key, value in row.items()} for row in rows)
    return out.getvalue()


async def _report_rows(name: str, session: AsyncSession, days: int, tz: str) -> list[dict]:
    match name:
        case "top":
            return await service.top(session, "songs", 50, days)
        case "top-artists":
            return await service.top(session, "artists", 50, days)
        case "genres":
            return await service.genres(session, days)
        case "plays":
            return await service.plays(session, "day", days, tz)
        case "plays-hourly":
            return await service.plays(session, "hour", days, tz)
        case "heatmap":
            return await service.heatmap(session, days, tz)
        case "catalog-sources":
            return [{"source": s, "count": c} for s, c in sorted((await catalog_by_source()).items())]
        case "user-growth":
            return [dataclasses.asdict(p) for p in await user_growth(days)]
        case "tape-activity":
            return [dataclasses.asdict(await tape_activity())]
        case "releases":
            return [dataclasses.asdict(await release_counts())]
        case "latency":
            return await service.latency(session, 1440)
        case "duplicates":
            return [{"duplicates_discarded": await duplicates_discarded()}]
    raise AppError(404, "report_not_found", "Ese reporte no existe")


@router.get("/admin/reports/{name}.csv")
async def report(
    name: str,
    days: int = Days,
    tz: str = Depends(_time_zone),
    _: CurrentUser = Depends(is_admin),
    session: AsyncSession = Depends(get_session),
):
    body = _to_csv(await _report_rows(name, session, days, tz))
    headers = {"Content-Disposition": f'attachment; filename="meloxo-{name}.csv"'}
    return Response(body, media_type="text/csv; charset=utf-8", headers=headers)
