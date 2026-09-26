from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user_id
from app.schemas import TaskCreate, TaskRead
from app.services.task_service import task_service

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, user_id: str = Depends(get_current_user_id)) -> TaskRead:
    return await task_service.create_task(user_id, payload)


@router.get("/tasks", response_model=list[TaskRead])
async def list_tasks(user_id: str = Depends(get_current_user_id)) -> list[TaskRead]:
    return await task_service.list_tasks(user_id)


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task_id: str, user_id: str = Depends(get_current_user_id)) -> TaskRead:
    return await task_service.get_task(user_id, task_id)


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: str, payload: TaskCreate, user_id: str = Depends(get_current_user_id)) -> TaskRead:
    return await task_service.update_task(user_id, task_id, payload)


@router.patch("/tasks/{task_id}/toggle-complete", response_model=TaskRead)
async def toggle_task(task_id: str, user_id: str = Depends(get_current_user_id)) -> TaskRead:
    return await task_service.toggle_complete(user_id, task_id)


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user_id: str = Depends(get_current_user_id)) -> dict[str, bool]:
    return await task_service.delete_task(user_id, task_id)
