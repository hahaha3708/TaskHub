from fastapi import APIRouter, status

from app.dependencies import AdminUser, CurrentUser, UserServiceDep
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdate,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> User:
    return await service.update_profile(current_user.id, payload)


@router.get("/", response_model=list[UserResponse])
async def list_users(
    _admin: AdminUser,
    service: UserServiceDep,
) -> list[User]:
    return await service.list_users()


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: AdminUser,
    service: UserServiceDep,
) -> User:
    return await service.update_user_as_admin(admin.id, user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    admin: AdminUser,
    service: UserServiceDep,
) -> None:
    await service.delete_user_as_admin(admin.id, user_id)
