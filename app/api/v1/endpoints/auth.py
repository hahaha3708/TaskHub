from fastapi import APIRouter, status

from app.dependencies import AuthServiceDep, CurrentUser
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: UserCreate, service: AuthServiceDep) -> User:
    """Đăng ký tài khoản mới. Role luôn là MEMBER (client không được chọn)."""
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    return await service.login(payload)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    """Đổi refresh token lấy cặp token mới (rotation)."""
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, service: AuthServiceDep) -> None:
    await service.logout(payload.refresh_token)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    service: AuthServiceDep,
) -> None:
    await service.change_password(current_user.id, payload)
