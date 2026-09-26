from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import Task
from app.schemas import TaskCreate, TaskRead


class TaskRepository:
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _to_read(task: Task) -> TaskRead:
        return TaskRead(
            id=task.id,
            title=task.title,
            description=task.description,
            due_at=task.due_at,
            priority=task.priority,
            is_completed=task.is_completed,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    async def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        async with self.session_factory() as session:
            task = Task(
                user_id=user_id,
                title=payload.title,
                description=payload.description,
                due_at=payload.due_at,
                priority=payload.priority,
                is_completed=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return self._to_read(task)

    async def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        async with self.session_factory() as session:
            result = await session.execute(select(Task).where(Task.user_id == user_id).order_by(Task.created_at.desc()))
            tasks = result.scalars().all()
            return [self._to_read(task) for task in tasks]

    async def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        async with self.session_factory() as session:
            result = await session.execute(select(Task).where(Task.user_id == user_id, Task.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return None
            return self._to_read(task)

    async def update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        async with self.session_factory() as session:
            result = await session.execute(select(Task).where(Task.user_id == user_id, Task.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                raise ValueError("Task not found")

            task.title = payload.title
            task.description = payload.description
            task.due_at = payload.due_at
            task.priority = payload.priority
            task.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(task)
            return self._to_read(task)

    async def toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        async with self.session_factory() as session:
            result = await session.execute(select(Task).where(Task.user_id == user_id, Task.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                raise ValueError("Task not found")

            task.is_completed = not task.is_completed
            task.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(task)
            return self._to_read(task)

    async def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        async with self.session_factory() as session:
            result = await session.execute(select(Task).where(Task.user_id == user_id, Task.id == task_id))
            task = result.scalar_one_or_none()
            if task is None:
                return False

            await session.delete(task)
            await session.commit()
            return True
