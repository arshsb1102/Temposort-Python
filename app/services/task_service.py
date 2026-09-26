from fastapi import HTTPException, status

from app.db.repositories.task_repository import TaskRepository
from app.schemas import TaskCreate, TaskRead


class TaskService:
    def __init__(self) -> None:
        self.repo = TaskRepository()

    async def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        return await self.repo.create_task(user_id, payload)

    async def list_tasks(self, user_id: str) -> list[TaskRead]:
        return await self.repo.list_tasks_for_user(user_id)

    async def get_task(self, user_id: str, task_id: str) -> TaskRead:
        task = await self.repo.get_task_for_user(user_id, task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    async def update_task(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        try:
            return await self.repo.update_task_for_user(user_id, task_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    async def toggle_complete(self, user_id: str, task_id: str) -> TaskRead:
        try:
            return await self.repo.toggle_task_for_user(user_id, task_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    async def delete_task(self, user_id: str, task_id: str) -> dict[str, bool]:
        deleted = await self.repo.delete_task_for_user(user_id, task_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return {"deleted": True}


task_service = TaskService()
