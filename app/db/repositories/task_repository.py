from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.db.repositories.base import BaseRepository
from app.schemas import TaskCreate, TaskRead


class TaskRepository(BaseRepository):
    def _task_from_row(self, row: dict[str, Any]) -> TaskRead:
        return TaskRead(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            due_at=self._parse_datetime_value(row.get("due_at")),
            priority=row["priority"],
            is_completed=bool(row["is_completed"]),
            created_at=self._parse_datetime_value(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=self._parse_datetime_value(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        task_id = __import__("uuid").uuid4().hex
        now = datetime.now(timezone.utc)
        task = TaskRead(
            id=task_id,
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
            priority=payload.priority,
            is_completed=False,
            created_at=now,
            updated_at=now,
        )
        with self.session.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (id, user_id, title, description, due_at, priority, is_completed, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    task.id,
                    user_id,
                    task.title,
                    task.description,
                    task.due_at,
                    task.priority,
                    task.is_completed,
                    task.created_at,
                    task.updated_at,
                ),
            )
        self.session.connection.commit()
        return task

    async def async_create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        return await asyncio.to_thread(self.create_task, user_id, payload)

    def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        with self.session.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
        return [self._task_from_row(row) for row in rows]

    async def async_list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        return await asyncio.to_thread(self.list_tasks_for_user, user_id)

    def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        with self.session.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND id = %s", (user_id, task_id))
            row = cursor.fetchone()
        if row is None:
            return None
        return self._task_from_row(row)

    async def async_get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        return await asyncio.to_thread(self.get_task_for_user, user_id, task_id)

    def update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        task = self.get_task_for_user(user_id, task_id)
        if task is None:
            raise ValueError("Task not found")

        updated = TaskRead(
            id=task.id,
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
            priority=payload.priority,
            is_completed=task.is_completed,
            created_at=task.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        with self.session.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET title = %s, description = %s, due_at = %s, priority = %s, updated_at = %s
                WHERE user_id = %s AND id = %s
                """,
                (
                    updated.title,
                    updated.description,
                    updated.due_at,
                    updated.priority,
                    updated.updated_at,
                    user_id,
                    task_id,
                ),
            )
        self.session.connection.commit()
        return updated

    async def async_update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        return await asyncio.to_thread(self.update_task_for_user, user_id, task_id, payload)

    def toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        task = self.get_task_for_user(user_id, task_id)
        if task is None:
            raise ValueError("Task not found")

        task.is_completed = not task.is_completed
        task.updated_at = datetime.now(timezone.utc)
        with self.session.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET is_completed = %s, updated_at = %s WHERE user_id = %s AND id = %s",
                (task.is_completed, task.updated_at, user_id, task_id),
            )
        self.session.connection.commit()
        return task

    async def async_toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        return await asyncio.to_thread(self.toggle_task_for_user, user_id, task_id)

    def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        with self.session.cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE user_id = %s AND id = %s", (user_id, task_id))
            deleted = cursor.rowcount > 0
        self.session.connection.commit()
        return deleted

    async def async_delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        return await asyncio.to_thread(self.delete_task_for_user, user_id, task_id)
