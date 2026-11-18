from sqlalchemy import select

from app.core import messages
from app.core.constants import TASK_NOT_FOUND
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.enums import WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def list_tasks(self, user_id: int) -> list[Task]:
        return await self.repository.list_visible_to(user_id)

    async def get_task(self, task_id: int, user_id: int) -> Task:
        task = await self.repository.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)
        await self._check_project_access(task.project_id, user_id)
        return task

    async def create_task(self, payload: TaskCreate, user_id: int) -> Task:
        await self._check_project_access(payload.project_id, user_id, write=True)
        return await self.repository.create_for_user(payload, user_id)

    async def update_task(
        self, task_id: int, payload: TaskUpdate, user_id: int
    ) -> Task:
        task = await self.get_task(task_id, user_id)
        await self._check_project_access(task.project_id, user_id, write=True)
        return await self.repository.update(task, payload)

    async def delete_task(self, task_id: int, user_id: int) -> None:
        task = await self.get_task(task_id, user_id)
        await self._check_project_access(task.project_id, user_id, write=True)
        await self.repository.delete(task)

    async def _check_project_access(
        self, project_id: int, user_id: int, *, write: bool = False
    ) -> None:
        project = await self.repository.session.get(Project, project_id)
        if project is None:
            raise NotFoundException(messages.NOT_FOUND)
        workspace = await self.repository.session.get(Workspace, project.workspace_id)
        if workspace is None:
            raise NotFoundException(messages.WORKSPACE_NOT_FOUND)
        membership = await self.repository.session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if workspace.owner_id == user_id or (
            membership is not None
            and (
                not write
                or membership.role in (WorkspaceRole.OWNER, WorkspaceRole.EDITOR)
            )
        ):
            return
        raise ForbiddenException(messages.WORKSPACE_ACCESS_DENIED)
