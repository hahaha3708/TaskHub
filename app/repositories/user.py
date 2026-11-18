from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_active_admins(self) -> int:
        from app.models.enums import UserRole

        statement = select(User).where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
        result = await self.session.execute(statement)
        return len(list(result.scalars().all()))

    async def lock_active_admins(self) -> list[User]:
        """Lock active admin rows while checking last-admin safeguards."""
        from app.models.enums import UserRole

        statement = (
            select(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
            .with_for_update()
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
