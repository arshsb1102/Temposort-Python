from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.schemas import TaskCreate, TaskRead


class InMemoryStore:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.tasks: dict[str, dict[str, Any]] = {}

    def clear(self) -> None:
        self.users.clear()
        self.tasks.clear()

    def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        email_key = email.lower()
        if email_key in self.users:
            raise ValueError("Email already registered.")

        user_id = str(uuid4())
        user = {
            "id": user_id,
            "name": name,
            "email": email_key,
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc),
        }
        self.users[email_key] = user
        return user

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.users.get(email.lower())

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        for user in self.users.values():
            if user["id"] == user_id:
                return user
        return None

    def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        task_id = str(uuid4())
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
        self.tasks[task_id] = {
            "user_id": user_id,
            "task": task.model_dump(),
        }
        return task

    def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        tasks: list[TaskRead] = []
        for task_record in self.tasks.values():
            if task_record["user_id"] == user_id:
                tasks.append(TaskRead(**task_record["task"]))
        return tasks

    def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        task_record = self.tasks.get(task_id)
        if task_record is None or task_record["user_id"] != user_id:
            return None
        return TaskRead(**task_record["task"])

    def update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        task_record = self.tasks.get(task_id)
        if task_record is None or task_record["user_id"] != user_id:
            raise ValueError("Task not found")

        task = TaskRead(**task_record["task"])
        task.title = payload.title
        task.description = payload.description
        task.due_at = payload.due_at
        task.priority = payload.priority
        task.updated_at = datetime.now(timezone.utc)
        task_record["task"] = task.model_dump()
        return task

    def toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        task_record = self.tasks.get(task_id)
        if task_record is None or task_record["user_id"] != user_id:
            raise ValueError("Task not found")

        task = TaskRead(**task_record["task"])
        task.is_completed = not task.is_completed
        task.updated_at = datetime.now(timezone.utc)
        task_record["task"] = task.model_dump()
        return task


store = InMemoryStore()
