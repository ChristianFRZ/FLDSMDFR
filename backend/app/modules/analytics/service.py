"""Consultas de las gráficas. Los datos del Compositor son agregados: nunca llevan identidades."""
import platform
import shutil
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.analytics.models import PlaysHourly, RequestMetric, UserPlays
from app.modules.catalog.public import get_artists, get_songs

UNAVAILABLE = "No disponible"
STARTED_AT = datetime.now(UTC)


def _since(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


async def _labels(session: AsyncSession, kind: str, ids: list[UUID]) -> dict[UUID, str]:
    await session.commit()  # Suelta la conexión mientras catálogo abre la suya.
    if kind == "artists":
        return {i: a.name for i, a in (await get_artists(ids)).items()}
    return {i: s.title for i, s in (await get_songs(ids)).items()}


async def top(
    session: AsyncSession, kind: str, limit: int, days: int, user_id: UUID | None = None
) -> list[dict]:
    model = PlaysHourly if user_id is None else UserPlays
    key = model.artist_id if kind == "artists" else model.song_id
    total = func.sum(model.plays)
    query = select(key, total).group_by(key).order_by(total.desc(), key).limit(limit)
    # El dato personal no tiene dimensión de tiempo: es de toda la historia de esa persona.
    query = query.where(PlaysHourly.hour >= _since(days)) if user_id is None else query.where(UserPlays.user_id == user_id)
    rows = (await session.execute(query)).all()
    labels = await _labels(session, kind, [r[0] for r in rows])
    return [{"id": i, "label": labels.get(i, UNAVAILABLE), "plays": int(plays)} for i, plays in rows]


async def genres(session: AsyncSession, days: int, user_id: UUID | None = None) -> list[dict]:
    model = PlaysHourly if user_id is None else UserPlays
    total = func.sum(model.plays)
    query = select(model.genre, total).group_by(model.genre).order_by(total.desc())
    query = query.where(PlaysHourly.hour >= _since(days)) if user_id is None else query.where(UserPlays.user_id == user_id)
    return [{"genre": g, "plays": int(p)} for g, p in (await session.execute(query)).all()]


async def plays(
    session: AsyncSession, group: str, days: int, tz: str, song_ids: list[UUID] | None = None
) -> list[dict]:
    local = func.timezone(tz, PlaysHourly.hour)
    bucket = func.date_trunc(group, local)
    query = (
        select(bucket, func.sum(PlaysHourly.plays))
        .where(PlaysHourly.hour >= _since(days))
        .group_by(bucket)
        .order_by(bucket)
    )
    if song_ids is not None:
        query = query.where(PlaysHourly.song_id.in_(song_ids))
    return [{"bucket": b, "plays": int(p)} for b, p in (await session.execute(query)).all()]


async def heatmap(session: AsyncSession, days: int, tz: str) -> list[dict]:
    local = func.timezone(tz, PlaysHourly.hour)
    dow, hour = extract("isodow", local), extract("hour", local)
    query = (
        select(dow, hour, func.sum(PlaysHourly.plays))
        .where(PlaysHourly.hour >= _since(days))
        .group_by(dow, hour)
        .order_by(dow, hour)
    )
    return [{"dow": int(d), "hour": int(h), "plays": int(p)} for d, h, p in (await session.execute(query)).all()]


async def latency(session: AsyncSession, minutes: int) -> list[dict]:
    since = datetime.now(UTC) - timedelta(minutes=minutes)
    query = select(RequestMetric).where(RequestMetric.minute >= since).order_by(RequestMetric.minute)
    return [
        {
            "minute": r.minute,
            "module": r.module,
            "count": r.count,
            "errors": r.errors,
            "p50_ms": round(r.p50_ms, 1),
            "p95_ms": round(r.p95_ms, 1),
        }
        for r in (await session.execute(query)).scalars()
    ]


def uptime_seconds() -> int:
    return int((datetime.now(UTC) - STARTED_AT).total_seconds())


def _disk() -> dict | None:
    try:
        usage = shutil.disk_usage(get_settings().MEDIA_DIR)
    except OSError:
        return None
    return {"used_bytes": usage.used, "total_bytes": usage.total}


async def system_status(session: AsyncSession) -> dict:
    database = (
        await session.execute(
            text(
                """
                SELECT pg_database_size(current_database()) AS size_bytes,
                       (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) AS connections,
                       current_setting('max_connections')::int AS max_connections,
                       current_setting('server_version') AS postgres
                """
            )
        )
    ).one()
    return {
        "disk": _disk(),
        "database": {
            "size_bytes": database.size_bytes,
            "connections": database.connections,
            "max_connections": database.max_connections,
        },
        "system": {
            "version": get_settings().APP_VERSION,
            "started_at": STARTED_AT,
            "python": platform.python_version(),
            "postgres": database.postgres.split()[0],
        },
    }
