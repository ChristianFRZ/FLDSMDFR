"""users-playlists falso: solo el conteo interno que usan las métricas."""

from fastapi import FastAPI


class FakeUsers:
    def __init__(self, count: int = 0) -> None:
        self.count = count
        self.app = FastAPI()

        @self.app.get("/internal/users/count")
        async def count_users():
            return {"count": self.count}
