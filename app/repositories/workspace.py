from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceRepository(BaseRepository[Workspace, WorkspaceCreate, WorkspaceUpdate]):
    model = Workspace

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_with_membership(
        self, workspace_id: int, user_id: int
    ) -> tuple[Workspace | None, WorkspaceMember | None]:
        """Lấy workspace kèm membership của user (nếu có)."""
        workspace = await self.get(workspace_id)
        if workspace is None:
            return None, None
        membership = await self.get_membership(workspace_id, user_id)
        return workspace, membership

    async def get_membership(
        self, workspace_id: int, user_id: int
    ) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        *,
        workspace_id: int,
        user_id: int,
        role,
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(member)
        return member

    async def remove_member(self, workspace_id: int, user_id: int) -> int:
        member = await self.get_membership(workspace_id, user_id)
        if member is None:
            return 0
        await self.session.delete(member)
        return 1
