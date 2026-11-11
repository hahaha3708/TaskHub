from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema shared by every request/response schema.

    ``str_strip_whitespace`` tự động loại bỏ khoảng trắng thừa ở mọi
    trường chuỗi và đồng bộ ``str_strip_whitespace`` với ``from_attributes``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)


class BaseResponseSchema(BaseSchema):
    model_config = ConfigDict(from_attributes=True)
