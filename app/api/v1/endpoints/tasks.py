from fastapi import APIRouter, status

from app.dependencies import TaskServiceDep
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, service: TaskServiceDep) -> Task:
    return service.create_task(payload)


@router.get("/", response_model=list[TaskResponse])
def list_tasks(service: TaskServiceDep) -> list[Task]:
    return service.list_tasks()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, service: TaskServiceDep) -> Task:
    return service.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    service: TaskServiceDep,
) -> Task:
    return service.update_task(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, service: TaskServiceDep) -> None:
    service.delete_task(task_id)
