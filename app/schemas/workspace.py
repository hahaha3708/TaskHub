from datetime import datetime

from pydantic import Field

from app.core.constants import TITLE_MAX_LENGTH, TITLE_MIN_LENGTH
from app.models.enums import WorkspaceRole
from app.schemas.base import BaseResponseSchema, BaseSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)


class WorkspaceUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH
    )


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
