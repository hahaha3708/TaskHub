from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository cho refresh token, đặc biệt là rotation atomic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, jti: str, user_id: int, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            revoked=False,
        )
        self.session.add(token)
        return token

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_by_jti(self, jti: str) -> RefreshToken | None:
        """Revoke một token theo jti (không cần atomic, dùng cho logout)."""
        statement = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(revoked=True)
            .returning(RefreshToken)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def atomic_revoke_unrevoked(self, jti: str) -> RefreshToken | None:
        """Revoke token một cách atomic.

        Dùng ``UPDATE ... WHERE revoked = false RETURNING`` để chỉ có một
        request refresh thành công trong trường hợp 2 request song song dùng
        cùng một refresh token. Trả về token đã revoke, hoặc None nếu token
        không tồn tại / đã bị revoke.
        """
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.jti == jti,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
            .returning(RefreshToken)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke_all_for_user(self, user_id: int) -> int:
        """Revoke tất cả refresh token của user (dùng khi phát hiện reuse
        hoặc đổi mật khẩu). Trả về số dòng bị ảnh hưởng."""
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )
        result = await self.session.execute(statement)
        return result.rowcount or 0

    async def is_expired(self, token: RefreshToken) -> bool:
        return token.expires_at < datetime.now(UTC)
