"""Mật khẩu băm và tạo / giải mã JWT.

- Mật khẩu dùng ``bcrypt`` trực tiếp (passlib không tương thích bcrypt >=4.1).
  bcrypt bỏ qua byte sau thứ 72, nên schema phải chặn mật khẩu dài hơn 72 byte
  (xem ``PASSWORD_MAX_BYTES``).
- JWT claims: ``sub`` (user id), ``type`` (access/refresh), ``jti``, ``iat``,
  ``exp``. Khi decode kiểm tra ``type`` khớp để refresh token không dùng được
  như access token.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import InvalidTokenException
from app.models.enums import TokenType


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def _create_token(
    user_id: int, token_type: TokenType, expires_delta: timedelta
) -> tuple[str, str]:
    """Tạo JWT. Trả về ``(token, jti)``."""
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type.value,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, jti


def create_access_token(user_id: int) -> tuple[str, str]:
    delta = timedelta(minutes=settings.access_token_expire_minutes)
    return _create_token(user_id, TokenType.ACCESS, delta)


def create_refresh_token(user_id: int) -> tuple[str, str]:
    delta = timedelta(days=settings.refresh_token_expire_days)
    return _create_token(user_id, TokenType.REFRESH, delta)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Giải mã và kiểm tra token.

    - Ký hiệu không hợp lệ / hết hạn / sai ``type`` → InvalidTokenException (401).
    - ``sub`` parse lỗi (ValueError/KeyError) cũng → 401, không để ra 500.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenException() from exc

    token_type = payload.get("type")
    if token_type != expected_type.value:
        raise InvalidTokenException()

    try:
        sub = payload["sub"]
        user_id = int(sub)
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenException() from exc

    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise InvalidTokenException()

    return {"user_id": user_id, "jti": jti, "type": token_type}
