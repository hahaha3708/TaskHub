from dataclasses import dataclass
from datetime import datetime

from app.schemas.task import TaskPriority, TaskStatus


@dataclass
class Task:
    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
