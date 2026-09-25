from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] = "medium"


class TaskRead(TaskCreate):
    id: str
    is_completed: bool = False
    created_at: datetime
    updated_at: datetime
