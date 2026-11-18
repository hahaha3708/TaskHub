from pydantic import Field, field_validator

from app.core.constants import (
    LABEL_COLOR_MAX_LENGTH,
    LABEL_NAME_MAX_LENGTH,
    LABEL_NAME_MIN_LENGTH,
)
from app.schemas.base import BaseResponseSchema, BaseSchema


class LabelCreate(BaseSchema):
    name: str = Field(
        ...,
        min_length=LABEL_NAME_MIN_LENGTH,
        max_length=LABEL_NAME_MAX_LENGTH,
    )
    color: str = Field(
        ...,
        min_length=1,
        max_length=LABEL_COLOR_MAX_LENGTH,
    )


class LabelUpdate(BaseSchema):
    name: str | None = Field(
        default=None,
        min_length=LABEL_NAME_MIN_LENGTH,
        max_length=LABEL_NAME_MAX_LENGTH,
    )
    color: str | None = Field(
        default=None,
        min_length=1,
        max_length=LABEL_COLOR_MAX_LENGTH,
    )

    @field_validator("name", mode="before")
    @classmethod
    def reject_null_name(cls, value: object) -> object:
        if value is None:
            raise ValueError("name cannot be null")
        return value

    @field_validator("color", mode="before")
    @classmethod
    def reject_null_color(cls, value: object) -> object:
        if value is None:
            raise ValueError("color cannot be null")
        return value


class LabelResponse(BaseResponseSchema):
    id: int
    project_id: int
    name: str
    color: str
