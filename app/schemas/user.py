from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    FULL_NAME_MIN_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
)
from app.models.enums import UserRole
from app.schemas.base import BaseResponseSchema, BaseSchema


def _validate_password_bytes(value: str) -> str:
    """bcrypt chỉ xử lý 72 byte đầu tiên. Chặn mật khẩu dài hơn 72 byte."""
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(
            f"password must be at most {PASSWORD_MAX_BYTES} bytes "
            f"(got {len(value.encode('utf-8'))})"
        )
    return value


class UserBase(BaseSchema):
    email: EmailStr = Field(..., max_length=EMAIL_MAX_LENGTH)
    full_name: str = Field(
        ..., min_length=FULL_NAME_MIN_LENGTH, max_length=FULL_NAME_MAX_LENGTH
    )


class UserCreate(UserBase):
    """Đăng ký. Client KHÔNG được tự chọn role — server luôn gán MEMBER."""

    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("password")
    @classmethod
    def _check_password_bytes(cls, value: str) -> str:
        return _validate_password_bytes(value)


class UserUpdate(BaseSchema):
    """User tự cập nhật profile của mình."""

    email: EmailStr | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    full_name: str | None = Field(
        default=None,
        min_length=FULL_NAME_MIN_LENGTH,
        max_length=FULL_NAME_MAX_LENGTH,
    )


class UserAdminUpdate(BaseSchema):
    """Admin cập nhật user khác (email, full_name, role, is_active)."""

    email: EmailStr | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    full_name: str | None = Field(
        default=None,
        min_length=FULL_NAME_MIN_LENGTH,
        max_length=FULL_NAME_MAX_LENGTH,
    )
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseResponseSchema):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class ChangePasswordRequest(BaseSchema):
    old_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("old_password", "new_password")
    @classmethod
    def _check_password_bytes(cls, value: str) -> str:
        return _validate_password_bytes(value)
