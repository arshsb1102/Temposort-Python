from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.reminder_service import reminder_service


class SchedulerService:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.add_job(
                reminder_service.process_due_reminders,
                trigger=CronTrigger(minute="*/30"),
                id="due-reminder-processor",
                replace_existing=True,
            )
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)


scheduler_service = SchedulerService()
