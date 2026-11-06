from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    DESCRIPTION_MAX_LENGTH,
    PRIORITY_CANNOT_BE_NULL,
    STATUS_CANNOT_BE_NULL,
    TITLE_CANNOT_BE_NULL,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
)
from app.models.enums import TaskPriority, TaskStatus


class TaskSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class TaskCreate(TaskSchema):
    title: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None


class TaskUpdate(TaskSchema):
    title: str | None = Field(
        default=None,
        min_length=TITLE_MIN_LENGTH,
        max_length=TITLE_MAX_LENGTH,
    )
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title", mode="before")
    @classmethod
    def reject_null_title(cls, value: object) -> object:
        if value is None:
            raise ValueError(TITLE_CANNOT_BE_NULL)
        return value

    @field_validator("status", mode="before")
    @classmethod
    def reject_null_status(cls, value: object) -> object:
        if value is None:
            raise ValueError(STATUS_CANNOT_BE_NULL)
        return value

    @field_validator("priority", mode="before")
    @classmethod
    def reject_null_priority(cls, value: object) -> object:
        if value is None:
            raise ValueError(PRIORITY_CANNOT_BE_NULL)
        return value


class TaskResponse(TaskSchema):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
