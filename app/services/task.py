from app.core.constants import TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.models.task import Task
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def list_tasks(self) -> list[Task]:
        return self.repository.list()

    def get_task(self, task_id: int) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)
        return task

    def create_task(self, payload: TaskCreate) -> Task:
        return self.repository.add(payload)

    def update_task(self, task_id: int, payload: TaskUpdate) -> Task:
        task = self.repository.update(task_id, payload)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)
        return task

    def delete_task(self, task_id: int) -> None:
        deleted = self.repository.remove(task_id)
        if not deleted:
            raise NotFoundException(TASK_NOT_FOUND)
