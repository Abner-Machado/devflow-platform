"""Task schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Priority, TaskStatus
from app.schemas.user import UserSummary


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    due_date: datetime | None = None
    assignee_id: uuid.UUID | None = None


class TaskCreate(TaskBase):
    project_id: uuid.UUID


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: Priority | None = None
    due_date: datetime | None = None
    assignee_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    due_date: datetime | None
    completed_at: datetime | None
    project_id: uuid.UUID
    assignee_id: uuid.UUID | None
    assignee: UserSummary | None = None
    project_name: str | None = None
    created_at: datetime
    updated_at: datetime
