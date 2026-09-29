from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user_id
from app.schemas import ReminderCreate, ReminderRead
from app.services.reminder_service import reminder_service

router = APIRouter(prefix="/api/v1", tags=["reminders"])
logger = logging.getLogger(__name__)


@router.post("/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(payload: ReminderCreate, user_id: str = Depends(get_current_user_id)) -> ReminderRead:
    return await reminder_service.create_reminder(user_id, payload)


@router.get("/reminders", response_model=list[ReminderRead])
async def list_reminders(user_id: str = Depends(get_current_user_id)) -> list[ReminderRead]:
    return await reminder_service.list_reminders(user_id)


@router.post("/reminders/process", status_code=status.HTTP_202_ACCEPTED)
async def queue_due_reminders(user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    try:
        task_id = await reminder_service.enqueue_due_reminder_processing(user_id)
    except Exception as exc:
        logger.exception("Could not enqueue due reminder processing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reminder queue is unavailable",
        ) from exc
    return {"status": "queued", "task_id": task_id}
