from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    role: str
    status: str
    created_at: datetime


class ProfilePatch(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class RoleIn(BaseModel):
    role: Literal["listener", "composer", "admin"]


class ReasonIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class OptionalReasonIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ComposerRequestIn(BaseModel):
    message: str = Field(default="", max_length=500)


class ComposerRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    message: str
    status: str
    reason: str | None
    created_at: datetime


class ComposerRequestAdminOut(ComposerRequestOut):
    user_name: str
    user_email: str


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: str
    target_type: str
    target_id: str
    detail: dict | None
    outcome: str
    created_at: datetime
