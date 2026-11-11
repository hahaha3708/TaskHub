from pydantic import Field, field_validator

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
)
from app.schemas.base import BaseSchema
from app.schemas.user import _validate_password_bytes


class LoginRequest(BaseSchema):
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("password")
    @classmethod
    def _check_password_bytes(cls, value: str) -> str:
        return _validate_password_bytes(value)


class RefreshRequest(BaseSchema):
    refresh_token: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
