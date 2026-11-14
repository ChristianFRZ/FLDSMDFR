"""users-playlists simulado con respx: solo la ruta de estado de autenticación."""
import asyncio
from uuid import UUID, uuid4

import httpx

USERS_URL = "http://users.test"


class FakeUsers:
    def __init__(self, router):
        self.users: dict[UUID, dict] = {}
        self.calls: list[httpx.Request] = []
        self.down = False
        router.get(url__regex=rf"{USERS_URL}/internal/users/(?P<user_id>[^/]+)/auth-state", name="usr_auth").mock(
            side_effect=self._auth_state
        )

    def add_user(self, role="listener", status="active") -> UUID:
        user_id = uuid4()
        self.users[user_id] = {"id": str(user_id), "role": role, "status": status}
        return user_id

    async def _auth_state(self, request, user_id):
        self.calls.append(request)
        await asyncio.sleep(0)
        if self.down:
            raise httpx.ConnectError("usuarios caído")
        found = self.users.get(UUID(user_id))
        if found is None:
            return httpx.Response(404, json={"error": {"code": "not_found", "message": "Usuario no encontrado"}})
        return httpx.Response(200, json=found)
