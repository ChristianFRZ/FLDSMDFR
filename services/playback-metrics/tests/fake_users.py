"""users-playlists simulado con respx: las rutas `/internal/*` que usa playback-metrics."""
import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

USERS_URL = "http://users.test"


class FakeUsers:
    def __init__(self, router):
        self.users: dict[UUID, dict] = {}
        self.playlists: list[set[UUID]] = []
        self.tapes: list[set[UUID]] = []
        self.calls: list[httpx.Request] = []
        self.down = False
        router.get(url__regex=rf"{USERS_URL}/internal/users/(?P<user_id>[^/]+)/auth-state", name="usr_auth").mock(
            side_effect=self._auth_state
        )
        router.get(f"{USERS_URL}/internal/users/growth", name="usr_growth").mock(side_effect=self._growth)
        router.get(f"{USERS_URL}/internal/playlists/inclusions", name="usr_playlists").mock(
            side_effect=lambda r: self._inclusions(r, self.playlists)
        )
        router.get(f"{USERS_URL}/internal/tapes/inclusions", name="usr_tapes").mock(
            side_effect=lambda r: self._inclusions(r, self.tapes)
        )
        router.get(f"{USERS_URL}/internal/tapes/activity", name="usr_activity").mock(side_effect=self._activity)

    # Lo que hacen las pruebas para preparar usuarios

    def add_user(self, role="listener", status="active") -> UUID:
        user_id = uuid4()
        self.users[user_id] = {"id": str(user_id), "role": role, "status": status}
        return user_id

    def add_playlist(self, song_ids) -> None:
        self.playlists.append({s.id if hasattr(s, "id") else s for s in song_ids})

    def add_tape(self, song_ids) -> None:
        self.tapes.append({s.id if hasattr(s, "id") else s for s in song_ids})

    async def _gate(self, request: httpx.Request) -> None:
        self.calls.append(request)
        await asyncio.sleep(0)
        if self.down:
            raise httpx.ConnectError("usuarios caído")

    async def _auth_state(self, request, user_id):
        await self._gate(request)
        found = self.users.get(UUID(user_id))
        if found is None:
            return httpx.Response(404, json={"error": {"code": "not_found", "message": "Usuario no encontrado"}})
        return httpx.Response(200, json=found)

    async def _growth(self, request):
        await self._gate(request)
        counts = {role: sum(u["role"] == role for u in self.users.values()) for role in ("listener", "composer", "admin")}
        return httpx.Response(200, json=[{"day": datetime.now(UTC).date().isoformat(), **counts}])

    async def _inclusions(self, request, containers):
        await self._gate(request)
        ids = {UUID(p) for p in request.url.params.get("song_ids", "").split(",") if p}
        return httpx.Response(200, json={"count": sum(bool(c & ids) for c in containers)})

    async def _activity(self, request):
        await self._gate(request)
        return httpx.Response(
            200, json={"tapes": len(self.tapes), "members": 0, "tracks": sum(len(t) for t in self.tapes), "dedications": 0}
        )
