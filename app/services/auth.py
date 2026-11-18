from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    InactiveUserException,
    InvalidTokenException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import TokenType, UserRole
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import ChangePasswordRequest, UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)

    async def register(self, payload: UserCreate) -> User:
        """Đăng ký. Role luôn là MEMBER — client không được tự chọn."""
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=UserRole.MEMBER,
        )
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            msg = str(exc.orig).lower() if exc.orig else ""
            if "email" in msg:
                raise ConflictException(messages.EMAIL_ALREADY_REGISTERED) from exc
            raise
        await self.session.refresh(user)
        return user

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException(messages.INVALID_CREDENTIALS)
        if not user.is_active:
            raise UnauthorizedException(messages.INACTIVE_USER)
        return await self._issue_tokens(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Lấy cặp token mới từ refresh token.

        Toàn bộ flow (revoke cũ + tạo mới + lưu) nằm trong một transaction.
        Revoke cũ là atomic (UPDATE ... WHERE revoked=false RETURNING) nên 2
        request song song cùng token chỉ có một cái thành công.
        """
        claims = decode_token(refresh_token, TokenType.REFRESH)
        user_id = claims["user_id"]
        jti = claims["jti"]

        revoked = await self.refresh_repo.atomic_revoke_unrevoked(jti)
        if revoked is None:
            # Token đã bị revoke (có thể do reuse) → revoke toàn bộ session
            # của user đó để an toàn, rồi trả 401.
            await self.refresh_repo.revoke_all_for_user(user_id)
            await self.session.commit()
            raise InvalidTokenException(messages.REFRESH_TOKEN_REUSED)

        user = await self.user_repo.get(user_id)
        if user is None:
            await self.session.commit()
            raise InvalidTokenException()
        if not user.is_active:
            await self.session.commit()
            raise InactiveUserException()

        return await self._issue_tokens(user.id)

    async def logout(self, refresh_token: str) -> None:
        claims = decode_token(refresh_token, TokenType.REFRESH)
        await self.refresh_repo.revoke_by_jti(claims["jti"])
        await self.session.commit()

    async def change_password(
        self, user_id: int, payload: ChangePasswordRequest
    ) -> None:
        user = await self.user_repo.get(user_id)
        if user is None:
            raise InvalidTokenException()
        if not verify_password(payload.old_password, user.hashed_password):
            raise ForbiddenException(messages.OLD_PASSWORD_INCORRECT)
        user.hashed_password = hash_password(payload.new_password)
        # Đổi mật khẩu → revoke tất cả refresh token cũ của user.
        await self.refresh_repo.revoke_all_for_user(user_id)
        await self.session.commit()

    async def _issue_tokens(self, user_id: int) -> TokenResponse:
        access_token, _ = create_access_token(user_id)
        refresh_token, jti = create_refresh_token(user_id)
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )
        await self.refresh_repo.create(jti=jti, user_id=user_id, expires_at=expires_at)
        await self.session.commit()
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
