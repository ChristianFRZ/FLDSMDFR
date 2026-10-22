from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    created_at: str
