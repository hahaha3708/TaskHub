from datetime import datetime

from pydantic import Field, field_validator

from app.core.constants import (
    PROJECT_DESCRIPTION_MAX_LENGTH,
    PROJECT_NAME_MAX_LENGTH,
    PROJECT_NAME_MIN_LENGTH,
)
from app.models.enums import ProjectStatus
from app.schemas.base import BaseResponseSchema, BaseSchema


class ProjectCreate(BaseSchema):
    name: str = Field(
        ...,
        min_length=PROJECT_NAME_MIN_LENGTH,
        max_length=PROJECT_NAME_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None,
        max_length=PROJECT_DESCRIPTION_MAX_LENGTH,
    )


class ProjectUpdate(BaseSchema):
    name: str | None = Field(
        default=None,
        min_length=PROJECT_NAME_MIN_LENGTH,
        max_length=PROJECT_NAME_MAX_LENGTH,
    )
    description: str | None = Field(
        default=None,
        max_length=PROJECT_DESCRIPTION_MAX_LENGTH,
    )

    @field_validator("name", mode="before")
    @classmethod
    def reject_null_name(cls, value: object) -> object:
        if value is None:
            raise ValueError("name cannot be null")
        return value


class ProjectResponse(BaseResponseSchema):
    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
