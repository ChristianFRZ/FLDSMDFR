"""Estado de los circuitos de este proceso, para la tarjeta "Resiliencia" de la Cabina."""

from fastapi import APIRouter, Depends

from app.clients import http
from app.shared import discovery
from app.shared.deps import require_admin

router = APIRouter(tags=["resiliencia"])


@router.get("/api/metrics/circuits", dependencies=[Depends(require_admin)])
async def circuits() -> dict:
    return {
        "instance": discovery.instance_id(),
        "circuits": [b.snapshot() for b in http.breakers()],
    }
