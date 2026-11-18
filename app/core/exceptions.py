"""Application exception hierarchy.

Mọi lỗi nghiệp vụ đều kế thừa :class:`AppException` để được xử lý bởi
handler toàn cục. Router / service / deps KHÔNG được raise ``HTTPException``
với message hardcode.
"""

from collections.abc import Mapping

from app.core import messages


class AppException(Exception):
    """Base exception for all application errors."""

    status_code: int = 400
    headers: Mapping[str, str] | None = None

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if headers is not None:
            self.headers = headers


class BadRequestException(AppException):
    status_code = 400


class UnauthorizedException(AppException):
    """401 errors. Luôn kèm header ``WWW-Authenticate: Bearer``."""

    status_code = 401
    headers = {"WWW-Authenticate": "Bearer"}

    def __init__(self, message: str = messages.INVALID_TOKEN) -> None:
        super().__init__(message)


class InvalidTokenException(UnauthorizedException):
    def __init__(self, message: str = messages.INVALID_TOKEN) -> None:
        super().__init__(message)


class InactiveUserException(UnauthorizedException):
    def __init__(self, message: str = messages.INACTIVE_USER) -> None:
        super().__init__(message)


class ForbiddenException(AppException):
    status_code = 403

    def __init__(self, message: str = messages.FORBIDDEN) -> None:
        super().__init__(message)


class NotFoundException(AppException):
    status_code = 404

    def __init__(self, message: str = messages.NOT_FOUND) -> None:
        super().__init__(message)


class ConflictException(AppException):
    status_code = 409

    def __init__(self, message: str) -> None:
        super().__init__(message)
