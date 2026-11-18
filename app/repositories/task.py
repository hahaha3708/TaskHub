from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.models.associations import task_labels
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.base import PaginationParams
from app.schemas.task import TaskCreate, TaskFilterParams, TaskUpdate


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, task_id: int) -> Task | None:
        statement = (
            select(Task).where(Task.id == task_id).options(selectinload(Task.labels))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: int,
        filters: TaskFilterParams,
        pagination: PaginationParams,
    ) -> tuple[list[Task], int]:
        conditions = [Task.project_id == project_id]
        if filters.status:
            conditions.append(Task.status.in_(filters.status))
        if filters.priority:
            conditions.append(Task.priority.in_(filters.priority))
        if filters.assignee_id is not None:
            conditions.append(Task.assignee_id == filters.assignee_id)

        count_stmt = select(func.count(Task.id)).where(*conditions)
        total = (await self.session.execute(count_stmt)).scalar_one()

        list_stmt = (
            select(Task)
            .where(*conditions)
            .options(selectinload(Task.labels))
            .order_by(Task.created_at.desc(), Task.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        items = list((await self.session.execute(list_stmt)).scalars().all())
        return items, int(total)

    async def list_visible_to(self, user_id: int) -> list[Task]:
        statement = (
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .join(Workspace, Project.workspace_id == Workspace.id)
            .outerjoin(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(
                or_(
                    Workspace.owner_id == user_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
            .options(selectinload(Task.labels))
            .order_by(Task.created_at.desc(), Task.id.desc())
            .distinct()
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_task(
        self, project_id: int, created_by: int, payload: TaskCreate
    ) -> Task:
        task = Task(
            project_id=project_id,
            created_by=created_by,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            assignee_id=payload.assignee_id,
            due_date=payload.due_date,
            status=TaskStatus.TODO,
        )
        self.session.add(task)
        await self.session.flush()
        # Ensure labels relation is populated without triggering lazy load
        set_committed_value(task, "labels", [])
        return task

    async def update_task(self, task: Task, payload: TaskUpdate) -> Task:
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(task, field, value)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def delete_task(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.flush()

    async def attach_label(self, task_id: int, label_id: int) -> None:
        statement = insert(task_labels).values(task_id=task_id, label_id=label_id)
        await self.session.execute(statement)
        await self.session.flush()

    async def detach_label(self, task_id: int, label_id: int) -> int:
        statement = delete(task_labels).where(
            task_labels.c.task_id == task_id,
            task_labels.c.label_id == label_id,
        )
        result = await self.session.execute(statement)
        await self.session.flush()
        return result.rowcount
