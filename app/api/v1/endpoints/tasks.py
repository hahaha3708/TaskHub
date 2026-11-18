from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import (
    CurrentUser,
    LabelId,
    PaginationDep,
    ProjectContextDep,
    TaskContextDep,
    TaskServiceDep,
)
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.schemas.base import PaginatedResponse
from app.schemas.task import (
    TaskCreate,
    TaskFilterParams,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter()


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_ctx: ProjectContextDep,
    current_user: CurrentUser,
    payload: TaskCreate,
    service: TaskServiceDep,
) -> Task:
    project_ctx.check_can_write()
    return await service.create_task(
        project_id=project_ctx.project.id,
        workspace_id=project_ctx.workspace.id,
        created_by=current_user.id,
        payload=payload,
    )


@router.get(
    "/projects/{project_id}/tasks",
    response_model=PaginatedResponse[TaskResponse],
)
async def list_project_tasks(
    project_ctx: ProjectContextDep,
    pagination: PaginationDep,
    service: TaskServiceDep,
    status_filter: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    priority_filter: Annotated[
        list[TaskPriority] | None, Query(alias="priority")
    ] = None,
    assignee_id: Annotated[int | None, Query(gt=0)] = None,
) -> PaginatedResponse[TaskResponse]:
    project_ctx.check_can_read()
    filters = TaskFilterParams(
        status=status_filter,
        priority=priority_filter,
        assignee_id=assignee_id,
    )
    return await service.list_project_tasks(project_ctx.project.id, filters, pagination)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_ctx: TaskContextDep) -> Task:
    task_ctx.check_can_read()
    return task_ctx.task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_ctx: TaskContextDep,
    payload: TaskUpdate,
    service: TaskServiceDep,
) -> Task:
    task_ctx.check_can_write()
    return await service.update_task(
        task=task_ctx.task,
        workspace_id=task_ctx.workspace.id,
        payload=payload,
    )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_ctx: TaskContextDep,
    service: TaskServiceDep,
) -> None:
    task_ctx.check_can_write()
    await service.delete_task(task_ctx.task)


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_200_OK,
)
async def attach_label_to_task(
    task_ctx: TaskContextDep,
    label_id: LabelId,
    service: TaskServiceDep,
) -> dict[str, str]:
    task_ctx.check_can_write()
    await service.attach_label(task_ctx.task, task_ctx.project.id, label_id)
    return {"message": "label attached successfully"}


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_label_from_task(
    task_ctx: TaskContextDep,
    label_id: LabelId,
    service: TaskServiceDep,
) -> None:
    task_ctx.check_can_write()
    await service.detach_label(task_ctx.task, label_id)


# Backward compatibility endpoint for day 2/3
@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> list[Task]:
    return await service.list_tasks(current_user.id)
