from fastapi import HTTPException, status

from app.db import store
from app.schemas import TaskCreate, TaskRead


class TaskService:
    def __init__(self) -> None:
        self.repo = store

    def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        return self.repo.create_task(user_id, payload)

    def list_tasks(self, user_id: str) -> list[TaskRead]:
        return self.repo.list_tasks_for_user(user_id)

    def get_task(self, user_id: str, task_id: str) -> TaskRead:
        task = self.repo.get_task_for_user(user_id, task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def update_task(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        try:
            return self.repo.update_task_for_user(user_id, task_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    def toggle_complete(self, user_id: str, task_id: str) -> TaskRead:
        try:
            return self.repo.toggle_task_for_user(user_id, task_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


task_service = TaskService()
