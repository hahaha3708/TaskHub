from sqlalchemy import or_, select

from app.models.project import Project
from app.models.task import Task
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    model = Task

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
            .distinct()
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_for_user(self, payload: TaskCreate, user_id: int) -> Task:
        task = Task(**payload.model_dump(), created_by=user_id)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task
