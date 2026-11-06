from app.core.constants import TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.models.task import Task
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def list_tasks(self) -> list[Task]:
        return await self.repository.list()

    async def get_task(self, task_id: int) -> Task:
        task = await self.repository.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)
        return task

    async def create_task(self, payload: TaskCreate) -> Task:
        return await self.repository.create(payload)

    async def update_task(self, task_id: int, payload: TaskUpdate) -> Task:
        task = await self.get_task(task_id)
        return await self.repository.update(task, payload)

    async def delete_task(self, task_id: int) -> None:
        task = await self.get_task(task_id)
        await self.repository.delete(task)
