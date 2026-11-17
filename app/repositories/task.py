from datetime import UTC, datetime
from threading import Lock

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._lock = Lock()

    def list(self) -> list[Task]:
        with self._lock:
            return list(self._tasks.values())

    def get(self, task_id: int) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def add(self, payload: TaskCreate) -> Task:
        with self._lock:
            task = Task(
                id=self._next_id,
                title=payload.title,
                description=payload.description,
                status=payload.status,
                priority=payload.priority,
                due_date=payload.due_date,
                created_at=datetime.now(UTC),
            )
            self._tasks[task.id] = task
            self._next_id += 1
            return task

    def update(self, task_id: int, payload: TaskUpdate) -> Task | None:
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                return None

            changes = payload.model_dump(exclude_unset=True)
            for field, value in changes.items():
                setattr(current, field, value)
            return current

    def remove(self, task_id: int) -> bool:
        with self._lock:
            if task_id not in self._tasks:
                return False
            del self._tasks[task_id]
            return True


task_repository = TaskRepository()
