from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas import ReminderCreate, ReminderRead
from app.services.reminder_service import reminder_service

router = APIRouter(prefix="/api/v1", tags=["reminders"])


@router.post("/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderCreate) -> ReminderRead:
    return reminder_service.create_reminder(payload)


@router.get("/reminders", response_model=list[ReminderRead])
def list_reminders() -> list[ReminderRead]:
    return reminder_service.repo.list_reminders()


@router.post("/reminders/process")
def process_due_reminders() -> dict[str, int | str]:
    processed = reminder_service.process_due_reminders()
    return {"processed": processed, "message": "Due reminders processed successfully."}
