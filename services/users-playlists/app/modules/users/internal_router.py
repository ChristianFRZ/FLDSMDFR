"""API interna de usuarios para otros servicios (red de Compose; el proxy no la expone)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users import service
from app.shared.deps import get_session

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


class CountOut(BaseModel):
    count: int


@router.get("/users/count", response_model=CountOut)
async def count_users(session: AsyncSession = Depends(get_session)) -> CountOut:
    return CountOut(count=await service.count_users(session))
