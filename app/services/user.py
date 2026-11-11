from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserAdminUpdate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_profile(self, user_id: int) -> User:
        user = await self.user_repo.get(user_id)
        if user is None:
            raise NotFoundException(messages.USER_NOT_FOUND)
        return user

    async def update_profile(self, user_id: int, payload: UserUpdate) -> User:
        user = await self.get_profile(user_id)
        return await self.user_repo.update(user, payload)

    async def list_users(self) -> list[User]:
        return await self.user_repo.list()

    async def get_user(self, user_id: int) -> User:
        user = await self.user_repo.get(user_id)
        if user is None:
            raise NotFoundException(messages.USER_NOT_FOUND)
        return user

    async def update_user_as_admin(
        self, admin_id: int, target_id: int, payload: UserAdminUpdate
    ) -> User:
        target = await self.get_user(target_id)

        # Nếu admin đang hạ quyền chính mình thành MEMBER, phải đảm bảo
        # còn ít nhất 1 admin active khác.
        # Nếu admin đang vô hiệu hoá / xoá quyền admin của mình:
        loses_admin_status = (
            target.role == UserRole.ADMIN
            and target.is_active
            and (payload.role == UserRole.MEMBER or payload.is_active is False)
        )
        if loses_admin_status:
            active_admins = await self.user_repo.lock_active_admins()
            # Nếu chính mình là admin duy nhất active thì không cho.
            remaining_admins = len(active_admins) - int(target in active_admins)
            if remaining_admins < 1:
                raise ForbiddenException(messages.CANNOT_DEMOTE_LAST_ADMIN)

        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(target, field, value)
        await self.session.commit()
        await self.session.refresh(target)
        return target

    async def delete_user_as_admin(self, admin_id: int, target_id: int) -> None:
        if admin_id == target_id:
            raise ForbiddenException(messages.CANNOT_DELETE_SELF)
        target = await self.get_user(target_id)
        # Không cho xoá admin active cuối cùng.
        if target.role == UserRole.ADMIN and target.is_active:
            active_admins = await self.user_repo.lock_active_admins()
            if len(active_admins) <= 1:
                raise ForbiddenException(messages.CANNOT_DEMOTE_LAST_ADMIN)
        await self.user_repo.delete(target)
