"""Project schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.enums import Priority, ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    status: ProjectStatus = ProjectStatus.PLANNING
    priority: Priority = Priority.MEDIUM
    repository_url: HttpUrl | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    """Every field optional: this is a partial update (PATCH semantics)."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    status: ProjectStatus | None = None
    priority: Priority | None = None
    repository_url: HttpUrl | None = None


class ProjectStats(BaseModel):
    """Derived counters. Never stored - always computed from the tasks table."""

    total_tasks: int = 0
    open_tasks: int = 0
    completed_tasks: int = 0
    document_count: int = 0
    progress: float = Field(
        default=0.0, ge=0, le=100, description="Completed tasks over total tasks, as a percentage."
    )


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    priority: Priority
    repository_url: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    stats: ProjectStats = ProjectStats()
