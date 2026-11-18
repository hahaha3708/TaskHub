from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberUpdate,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace_repo = WorkspaceRepository(session)

    async def create_workspace(
        self, owner_id: int, payload: WorkspaceCreate
    ) -> Workspace:
        workspace = Workspace(name=payload.name, owner_id=owner_id)
        self.session.add(workspace)
        await self.session.flush()
        # Owner tự động là thành viên với vai trò OWNER.
        await self.workspace_repo.add_member(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def get_workspace(self, workspace_id: int, user_id: int) -> Workspace:
        workspace, membership = await self.workspace_repo.get_with_membership(
            workspace_id, user_id
        )
        if workspace is None:
            raise NotFoundException(messages.WORKSPACE_NOT_FOUND)
        # Chỉ owner hoặc member (bất kỳ vai trò nào) mới được xem.
        if workspace.owner_id != user_id and membership is None:
            raise ForbiddenException(messages.WORKSPACE_ACCESS_DENIED)
        return workspace

    async def list_workspaces(self, user_id: int) -> list[Workspace]:
        return await self.workspace_repo.list_for_user(user_id)

    async def list_members(
        self, workspace_id: int, user_id: int
    ) -> list[WorkspaceMember]:
        await self.get_workspace(workspace_id, user_id)
        return await self.workspace_repo.list_members(workspace_id)

    async def update_workspace(
        self, workspace_id: int, user_id: int, payload: WorkspaceUpdate
    ) -> Workspace:
        workspace = await self._require_owner(workspace_id, user_id)
        return await self.workspace_repo.update(workspace, payload)

    async def delete_workspace(self, workspace_id: int, user_id: int) -> None:
        workspace = await self._require_owner(workspace_id, user_id)
        await self.workspace_repo.delete(workspace)

    async def add_member(
        self,
        workspace_id: int,
        owner_id: int,
        payload: WorkspaceMemberCreate,
    ) -> WorkspaceMember:
        await self._require_owner(workspace_id, owner_id)
        if payload.role == WorkspaceRole.OWNER:
            raise ForbiddenException(messages.CANNOT_ASSIGN_WORKSPACE_OWNER)
        user = await self.session.get(User, payload.user_id)
        if user is None or not user.is_active:
            raise NotFoundException(messages.WORKSPACE_USER_NOT_FOUND)
        existing = await self.workspace_repo.get_membership(
            workspace_id, payload.user_id
        )
        if existing is not None:
            raise ConflictException(messages.WORKSPACE_MEMBER_ALREADY_EXISTS)
        member = await self.workspace_repo.add_member(
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=payload.role,
        )
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(messages.WORKSPACE_MEMBER_ALREADY_EXISTS) from exc
        await self.session.refresh(member)
        return member

    async def update_member_role(
        self,
        workspace_id: int,
        owner_id: int,
        user_id: int,
        payload: WorkspaceMemberUpdate,
    ) -> WorkspaceMember:
        await self._require_owner(workspace_id, owner_id)
        membership = await self.workspace_repo.get_membership(workspace_id, user_id)
        if membership is None:
            raise NotFoundException(messages.WORKSPACE_MEMBER_NOT_FOUND)
        if membership.role == WorkspaceRole.OWNER:
            raise ForbiddenException(messages.WORKSPACE_OWNER_ROLE_IMMUTABLE)
        if payload.role == WorkspaceRole.OWNER:
            raise ForbiddenException(messages.CANNOT_ASSIGN_WORKSPACE_OWNER)
        return await self.workspace_repo.update_member_role(membership, payload.role)

    async def remove_member(
        self, workspace_id: int, owner_id: int, user_id: int
    ) -> None:
        await self._require_owner(workspace_id, owner_id)
        workspace, membership = await self.workspace_repo.get_with_membership(
            workspace_id, user_id
        )
        if workspace is None:
            raise NotFoundException(messages.WORKSPACE_NOT_FOUND)
        if membership is None:
            raise NotFoundException(messages.WORKSPACE_MEMBER_NOT_FOUND)
        if membership.role == WorkspaceRole.OWNER:
            raise ForbiddenException(messages.CANNOT_REMOVE_WORKSPACE_OWNER)
        await self.workspace_repo.remove_member(workspace_id, user_id)
        await self.session.commit()

    async def _require_owner(self, workspace_id: int, user_id: int) -> Workspace:
        workspace, _ = await self.workspace_repo.get_with_membership(
            workspace_id, user_id
        )
        if workspace is None:
            raise NotFoundException(messages.WORKSPACE_NOT_FOUND)
        if workspace.owner_id != user_id:
            raise ForbiddenException(messages.WORKSPACE_OWNER_ONLY)
        return workspace
