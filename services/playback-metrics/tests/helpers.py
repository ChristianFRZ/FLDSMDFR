"""Sesiones de prueba: este servicio no emite tokens, así que se firman aquí con el secreto
compartido, igual que lo haría users-playlists."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.shared.security import ALGORITHM


def make_token(role: str = "listener", user_id: uuid.UUID | None = None) -> str:
    claims = {
        "sub": str(user_id or uuid.uuid4()),
        "role": role,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=ALGORITHM)


async def signup(client: AsyncClient, **_ignored) -> dict:
    """Deja al cliente con la sesión de una persona oyente (cookie como en el navegador)."""
    user_id = uuid.uuid4()
    client.cookies.set(get_settings().cookie_name, make_token("listener", user_id))
    return {"user": {"id": str(user_id)}}


async def make_admin_client(_session: AsyncSession, client: AsyncClient) -> AsyncClient:
    admin = AsyncClient(transport=client._transport, base_url="http://test")
    admin.cookies.set(get_settings().cookie_name, make_token("admin"))
    return admin
