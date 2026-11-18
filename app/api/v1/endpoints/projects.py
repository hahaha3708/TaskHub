from fastapi import APIRouter, status

from app.dependencies import (
    PaginationDep,
    ProjectContextDep,
    ProjectServiceDep,
    WorkspaceContextDep,
)
from app.models.project import Project
from app.schemas.base import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    workspace_ctx: WorkspaceContextDep,
    payload: ProjectCreate,
    service: ProjectServiceDep,
) -> Project:
    workspace_ctx.check_can_write()
    return await service.create_project(workspace_ctx.workspace.id, payload)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=PaginatedResponse[ProjectResponse],
)
async def list_workspace_projects(
    workspace_ctx: WorkspaceContextDep,
    pagination: PaginationDep,
    service: ProjectServiceDep,
) -> PaginatedResponse[ProjectResponse]:
    workspace_ctx.check_can_read()
    return await service.list_projects(workspace_ctx.workspace.id, pagination)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(project_ctx: ProjectContextDep) -> Project:
    project_ctx.check_can_read()
    return project_ctx.project


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    project_ctx: ProjectContextDep,
    payload: ProjectUpdate,
    service: ProjectServiceDep,
) -> Project:
    project_ctx.check_can_write()
    return await service.update_project(project_ctx.project, payload)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_ctx: ProjectContextDep,
    service: ProjectServiceDep,
) -> None:
    project_ctx.check_can_write()
    await service.delete_project(project_ctx.project)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectResponse,
)
async def archive_project(
    project_ctx: ProjectContextDep,
    service: ProjectServiceDep,
) -> Project:
    project_ctx.check_can_change_archive()
    return await service.archive_project(project_ctx.project)


@router.post(
    "/projects/{project_id}/unarchive",
    response_model=ProjectResponse,
)
async def unarchive_project(
    project_ctx: ProjectContextDep,
    service: ProjectServiceDep,
) -> Project:
    project_ctx.check_can_change_archive()
    return await service.unarchive_project(project_ctx.project)
