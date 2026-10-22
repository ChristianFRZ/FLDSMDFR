from fastapi import APIRouter, HTTPException, status

from core.module_users.models import UserCreate, UserResponse
from core.module_users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    try:
        return UserService.create_user(payload)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("", response_model=list[UserResponse])
def list_users():
    return UserService.list_users()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con id {user_id} no encontrado.",
        )
    return user
