from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

ItemT = TypeVar("ItemT")


class BaseSchema(BaseModel):
    """Base schema shared by every request/response schema.

    ``str_strip_whitespace`` tự động loại bỏ khoảng trắng thừa ở mọi
    trường chuỗi và đồng bộ ``str_strip_whitespace`` với ``from_attributes``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)


class BaseResponseSchema(BaseSchema):
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    page: int = Field(
        default=DEFAULT_PAGE,
        ge=1,
        description="Page number starting at 1",
    )
    limit: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseSchema, Generic[ItemT]):
    items: list[ItemT]
    total: int
    page: int
    limit: int


__all__ = [
    "BaseResponseSchema",
    "BaseSchema",
    "PaginatedResponse",
    "PaginationParams",
    "PositiveInt",
]
