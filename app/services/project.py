from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.base import PaginatedResponse, PaginationParams
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate


class ProjectService:
    def __init__(
        self, session: AsyncSession, repository: ProjectRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or ProjectRepository(session)

    async def create_project(
        self, workspace_id: int, payload: ProjectCreate
    ) -> Project:
        project = await self.repository.create(workspace_id, payload)
        await self.session.commit()
        return project

    async def list_projects(
        self, workspace_id: int, pagination: PaginationParams
    ) -> PaginatedResponse[ProjectResponse]:
        items, total = await self.repository.list_by_workspace(workspace_id, pagination)
        return PaginatedResponse[ProjectResponse](
            items=[ProjectResponse.model_validate(p) for p in items],
            total=total,
            page=pagination.page,
            limit=pagination.limit,
        )

    async def update_project(self, project: Project, payload: ProjectUpdate) -> Project:
        updated = await self.repository.update(project, payload)
        await self.session.commit()
        return updated

    async def delete_project(self, project: Project) -> None:
        await self.repository.delete(project)
        await self.session.commit()

    async def archive_project(self, project: Project) -> Project:
        archived = await self.repository.archive(project)
        await self.session.commit()
        return archived

    async def unarchive_project(self, project: Project) -> Project:
        unarchived = await self.repository.unarchive(project)
        await self.session.commit()
        return unarchived
