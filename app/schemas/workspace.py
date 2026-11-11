from datetime import datetime

from pydantic import Field, field_validator

from app.core.constants import TITLE_MAX_LENGTH, TITLE_MIN_LENGTH
from app.core.messages import REQUIRED_FIELD_CANNOT_BE_NULL
from app.models.enums import WorkspaceRole
from app.schemas.base import BaseResponseSchema, BaseSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)


class WorkspaceUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH
    )

    @field_validator("name", mode="before")
    @classmethod
    def reject_null_name(cls, value: object) -> object:
        if value is None:
            raise ValueError(REQUIRED_FIELD_CANNOT_BE_NULL)
        return value


class WorkspaceResponse(BaseResponseSchema):
    id: int
    name: str
    owner_id: int
    created_at: datetime


class WorkspaceMemberCreate(BaseSchema):
    user_id: int
    role: WorkspaceRole = WorkspaceRole.VIEWER


class WorkspaceMemberResponse(BaseResponseSchema):
    workspace_id: int
    user_id: int
    role: WorkspaceRole
