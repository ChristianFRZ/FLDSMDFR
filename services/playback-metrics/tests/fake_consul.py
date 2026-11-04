"""Consul falso en memoria: la parte del API de agente y de salud que usa discovery.py."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class FakeConsul:
    def __init__(self) -> None:
        self.services: dict[str, dict] = {}  # id -> registro
        self.status: dict[str, str] = {}  # check id -> passing | critical
        self.passes = 0
        self.app = self._build()

    def add(self, name: str, instance_id: str, address: str, port: int = 8000) -> None:
        """Registra una instancia ajena (como si otro contenedor se hubiera registrado)."""
        self.services[instance_id] = {
            "ID": instance_id,
            "Name": name,
            "Address": address,
            "Port": port,
            "Check": {"CheckID": f"{instance_id}-ttl"},
        }
        self.status[f"{instance_id}-ttl"] = "passing"

    def kill(self, instance_id: str) -> None:
        """Como si el TTL hubiera vencido."""
        self.status[f"{instance_id}-ttl"] = "critical"

    def _build(self) -> FastAPI:
        app = FastAPI()

        @app.put("/v1/agent/service/register")
        async def register(request: Request):
            body = await request.json()
            self.services[body["ID"]] = body
            self.status[body["Check"]["CheckID"]] = "critical"  # TTL arranca sin latido
            return {}

        @app.put("/v1/agent/check/pass/{check_id}")
        async def check_pass(check_id: str):
            if check_id not in self.status:
                return JSONResponse({"error": "unknown check"}, status_code=404)
            self.status[check_id] = "passing"
            self.passes += 1
            return {}

        @app.put("/v1/agent/service/deregister/{instance_id}")
        async def deregister(instance_id: str):
            svc = self.services.pop(instance_id, None)
            if svc is not None:
                self.status.pop(svc["Check"]["CheckID"], None)
            return {}

        @app.get("/v1/health/service/{name}")
        async def health(name: str, passing: bool = False):
            out = []
            for svc in self.services.values():
                status = self.status.get(svc["Check"]["CheckID"], "critical")
                if svc["Name"] == name and (not passing or status == "passing"):
                    service = {k: svc[k] for k in ("ID", "Address", "Port")}
                    out.append({"Service": service, "Checks": [{"Status": status}]})
            return out

        return app
