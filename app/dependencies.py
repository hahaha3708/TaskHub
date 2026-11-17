from typing import Annotated

from fastapi import Depends

from app.repositories.task import TaskRepository, task_repository
from app.services.task import TaskService


def get_task_repository() -> TaskRepository:
    return task_repository


def get_task_service(
    repository: Annotated[TaskRepository, Depends(get_task_repository)],
) -> TaskService:
    return TaskService(repository=repository)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
