from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.schemas.base import PaginationParams
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: int) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list_by_workspace(
        self, workspace_id: int, pagination: PaginationParams
    ) -> tuple[list[Project], int]:
        condition = Project.workspace_id == workspace_id
        count_stmt = select(func.count(Project.id)).where(condition)
        total = (await self.session.execute(count_stmt)).scalar_one()

        list_stmt = (
            select(Project)
            .where(condition)
            .order_by(Project.created_at.desc(), Project.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        items = list((await self.session.execute(list_stmt)).scalars().all())
        return items, int(total)

    async def create(self, workspace_id: int, payload: ProjectCreate) -> Project:
        project = Project(
            workspace_id=workspace_id,
            name=payload.name,
            description=payload.description,
            status=ProjectStatus.ACTIVE,
        )
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def update(self, project: Project, payload: ProjectUpdate) -> Project:
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(project, field, value)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        await self.session.delete(project)
        await self.session.flush()

    async def archive(self, project: Project) -> Project:
        project.status = ProjectStatus.ARCHIVED
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def unarchive(self, project: Project) -> Project:
        project.status = ProjectStatus.ACTIVE
        await self.session.flush()
        await self.session.refresh(project)
        return project
