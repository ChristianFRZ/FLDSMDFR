from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

TapeColor = Annotated[str, StringConstraints(pattern=r"^(pink|yellow|teal|cobalt|#[0-9a-fA-F]{6})$")]


class TapeIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    color: TapeColor = "pink"


class TapePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=80)
    color: TapeColor | None = None


class TrackIn(BaseModel):
    song_id: UUID
    dedication: str | None = Field(default=None, max_length=140)


class OrderIn(BaseModel):
    version: int
    track_ids: list[UUID]


class InviteIn(BaseModel):
    """De un solo uso, o con expiración y límite de usos (F4.2)."""

    max_uses: int = Field(default=1, ge=1, le=100)
    expires_in_hours: int | None = Field(default=None, ge=1, le=720)

    @model_validator(mode="after")
    def many_uses_need_expiry(self):
        if self.max_uses > 1 and self.expires_in_hours is None:
            raise ValueError("Un enlace de varios usos necesita fecha de expiración")
        return self


@dataclass(frozen=True)
class TapeActivity:
    tapes: int
    members: int
    tracks: int
    dedications: int
