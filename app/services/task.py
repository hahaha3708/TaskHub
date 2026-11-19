from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.models.label import Label
from app.models.task import Task
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.task import TaskRepository
from app.schemas.base import PaginatedResponse, PaginationParams
from app.schemas.task import (
    TaskCreate,
    TaskFilterParams,
    TaskResponse,
    TaskUpdate,
)


class TaskService:
    def __init__(
        self, session: AsyncSession, repository: TaskRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or TaskRepository(session)

    async def list_project_tasks(
        self,
        project_id: int,
        filters: TaskFilterParams,
        pagination: PaginationParams,
    ) -> PaginatedResponse[TaskResponse]:
        items, total = await self.repository.list_by_project(
            project_id, filters, pagination
        )
        return PaginatedResponse[TaskResponse](
            items=[TaskResponse.model_validate(t) for t in items],
            total=total,
            page=pagination.page,
            limit=pagination.limit,
        )

    async def list_tasks(self, user_id: int) -> list[Task]:
        return await self.repository.list_visible_to(user_id)

    async def create_task(
        self,
        project_id: int,
        workspace_id: int,
        created_by: int,
        payload: TaskCreate,
    ) -> Task:
        await self._validate_assignee(workspace_id, payload.assignee_id)
        task = await self.repository.create_task(project_id, created_by, payload)
        await self.session.commit()
        return task

    async def update_task(
        self, task: Task, workspace_id: int, payload: TaskUpdate
    ) -> Task:
        if payload.assignee_id is not None:
            await self._validate_assignee(workspace_id, payload.assignee_id)
        updated = await self.repository.update_task(task, payload)
        await self.session.commit()
        loaded = await self.repository.get(task.id)
        return loaded or updated

    async def delete_task(self, task: Task) -> None:
        await self.repository.delete_task(task)
        await self.session.commit()

    async def attach_label(self, task: Task, project_id: int, label_id: int) -> None:
        label = await self.session.get(Label, label_id)
        if label is None:
            raise NotFoundException(messages.LABEL_NOT_FOUND)
        if label.project_id != project_id:
            raise UnprocessableEntityException(messages.LABEL_NOT_IN_PROJECT)

        try:
            await self.repository.attach_label(task.id, label_id)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(messages.LABEL_ALREADY_ATTACHED) from exc

    async def detach_label(self, task: Task, label_id: int) -> None:
        deleted_count = await self.repository.detach_label(task.id, label_id)
        if deleted_count == 0:
            raise NotFoundException(messages.LABEL_NOT_ATTACHED)
        await self.session.commit()

    async def _validate_assignee(
        self, workspace_id: int, assignee_id: int | None
    ) -> None:
        if assignee_id is None:
            return
        statement = (
            select(Workspace.id)
            .outerjoin(
                WorkspaceMember,
                and_(
                    WorkspaceMember.workspace_id == Workspace.id,
                    WorkspaceMember.user_id == assignee_id,
                ),
            )
            .where(
                Workspace.id == workspace_id,
                or_(
                    Workspace.owner_id == assignee_id,
                    WorkspaceMember.user_id == assignee_id,
                ),
            )
        )
        result = await self.session.execute(statement)
        is_member = result.scalar_one_or_none() is not None
        if not is_member:
            raise UnprocessableEntityException(messages.ASSIGNEE_NOT_IN_WORKSPACE)
