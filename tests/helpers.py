from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users import service as users_service


async def signup(
    client: AsyncClient,
    email: str = "oyente@test.mx",
    name: str = "Oyente",
    password: str = "secreta123",
) -> dict:
    r = await client.post(
        "/api/auth/register", json={"name": name, "email": email, "password": password}
    )
    assert r.status_code == 201, r.text
    return r.json()


async def make_admin_client(
    session: AsyncSession, client: AsyncClient, email: str = "admin@test.mx"
) -> AsyncClient:
    await users_service.ensure_user(session, "Admin", email, "admin12345", "admin")
    admin = AsyncClient(transport=client._transport, base_url="http://test")
    r = await admin.post("/api/auth/login", json={"email": email, "password": "admin12345"})
    assert r.status_code == 200, r.text
    return admin
