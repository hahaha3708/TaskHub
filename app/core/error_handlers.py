from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core import messages
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(
        _request: Request, exc: AppException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(
        _request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """Xử lý vi phạm ràng buộc duy nhất (vd: trùng email khi register).

        Không check-before-insert để tránh race condition: 2 request đồng thời
        cùng email sẽ chỉ có 1 thành công, request còn lại rơi vào đây.
        """
        logger.debug("IntegrityError: %s", exc.orig)
        msg = str(exc.orig).lower() if exc.orig else ""
        if "users" in msg and "email" in msg:
            detail = messages.EMAIL_ALREADY_REGISTERED
        else:
            detail = messages.DATA_CONFLICT
        return JSONResponse(
            status_code=409,
            content={"detail": detail},
        )
