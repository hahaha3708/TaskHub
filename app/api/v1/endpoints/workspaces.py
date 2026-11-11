from fastapi import APIRouter, status

from app.dependencies import CurrentUser, WorkspaceServiceDep
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> list[Workspace]:
    return await service.list_workspaces(current_user.id)


@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Workspace:
    return await service.create_workspace(current_user.id, payload)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Workspace:
    return await service.get_workspace(workspace_id, current_user.id)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> Workspace:
    return await service.update_workspace(workspace_id, current_user.id, payload)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: int,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> None:
    await service.delete_workspace(workspace_id, current_user.id)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    workspace_id: int,
    payload: WorkspaceMemberCreate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> WorkspaceMember:
    return await service.add_member(workspace_id, current_user.id, payload)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
)
async def list_members(
    workspace_id: int,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> list[WorkspaceMember]:
    return await service.list_members(workspace_id, current_user.id)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
)
async def update_member_role(
    workspace_id: int,
    user_id: int,
    payload: WorkspaceMemberUpdate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> WorkspaceMember:
    return await service.update_member_role(
        workspace_id,
        current_user.id,
        user_id,
        payload,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    workspace_id: int,
    user_id: int,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> None:
    await service.remove_member(workspace_id, current_user.id, user_id)
