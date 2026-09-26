from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas import ReminderCreate, ReminderRead
from app.services.reminder_service import reminder_service

router = APIRouter(prefix="/api/v1", tags=["reminders"])


@router.post("/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(payload: ReminderCreate) -> ReminderRead:
    return await reminder_service.create_reminder(payload)


@router.get("/reminders", response_model=list[ReminderRead])
async def list_reminders() -> list[ReminderRead]:
    return await reminder_service.list_reminders()


@router.post("/reminders/process")
async def process_due_reminders() -> dict[str, int | str]:
    processed = await reminder_service.process_due_reminders()
    return {"processed": processed, "message": "Due reminders processed successfully."}
