from datetime import datetime

from pydantic import Field, field_validator

from app.core.constants import (
    COMMENT_CONTENT_MAX_LENGTH,
    COMMENT_CONTENT_MIN_LENGTH,
)
from app.schemas.base import BaseResponseSchema, BaseSchema


class CommentCreate(BaseSchema):
    content: str = Field(
        ...,
        min_length=COMMENT_CONTENT_MIN_LENGTH,
        max_length=COMMENT_CONTENT_MAX_LENGTH,
    )


class CommentUpdate(BaseSchema):
    content: str = Field(
        ...,
        min_length=COMMENT_CONTENT_MIN_LENGTH,
        max_length=COMMENT_CONTENT_MAX_LENGTH,
    )

    @field_validator("content", mode="before")
    @classmethod
    def reject_null_content(cls, value: object) -> object:
        if value is None:
            raise ValueError("content cannot be null")
        return value


class CommentResponse(BaseResponseSchema):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
