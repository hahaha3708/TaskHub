from datetime import UTC, datetime

from pydantic import Field, field_validator

from app.core import messages
from app.core.constants import (
    DESCRIPTION_MAX_LENGTH,
    PRIORITY_CANNOT_BE_NULL,
    STATUS_CANNOT_BE_NULL,
    TITLE_CANNOT_BE_NULL,
    TITLE_MAX_LENGTH,
    TITLE_MIN_LENGTH,
)
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseResponseSchema, BaseSchema, PositiveInt
from app.schemas.label import LabelResponse


class TaskCreate(BaseSchema):
    title: str = Field(..., min_length=TITLE_MIN_LENGTH, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: PositiveInt | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            now = datetime.now(UTC)
            check_val = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
            if check_val < now:
                raise ValueError(messages.DUE_DATE_IN_PAST)
        return value


class TaskUpdate(BaseSchema):
    title: str | None = Field(
        default=None,
        min_length=TITLE_MIN_LENGTH,
        max_length=TITLE_MAX_LENGTH,
    )
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: PositiveInt | None = None
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

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            now = datetime.now(UTC)
            check_val = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
            if check_val < now:
                raise ValueError(messages.DUE_DATE_IN_PAST)
        return value


class TaskFilterParams(BaseSchema):
    status: list[TaskStatus] | None = None
    priority: list[TaskPriority] | None = None
    assignee_id: PositiveInt | None = None


class TaskResponse(BaseResponseSchema):
    id: int
    project_id: int
    created_by: int
    assignee_id: int | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
    labels: list[LabelResponse] = []
