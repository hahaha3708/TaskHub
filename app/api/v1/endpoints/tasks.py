from fastapi import APIRouter, status

from app.dependencies import CurrentUser, TaskServiceDep
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate, current_user: CurrentUser, service: TaskServiceDep
) -> Task:
    return await service.create_task(payload, current_user.id)


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(current_user: CurrentUser, service: TaskServiceDep) -> list[Task]:
    return await service.list_tasks(current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int, current_user: CurrentUser, service: TaskServiceDep
) -> Task:
    return await service.get_task(task_id, current_user.id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return await service.update_task(task_id, payload, current_user.id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int, current_user: CurrentUser, service: TaskServiceDep
) -> None:
    await service.delete_task(task_id, current_user.id)
