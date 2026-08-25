"""Metric schemas. Every field is computed from the database - nothing is faked."""

from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import Priority, TaskStatus


class MetricsOverview(BaseModel):
    total_projects: int = 0
    active_projects: int = 0
    completed_projects: int = 0
    total_tasks: int = 0
    open_tasks: int = 0
    completed_tasks: int = 0
    overdue_tasks: int = Field(default=0, description="Unfinished tasks past their due date.")
    total_documents: int = 0
    completion_rate: float = Field(
        default=0.0, ge=0, le=100, description="Completed tasks over total tasks, as a percentage."
    )


class ActivityPoint(BaseModel):
    """One calendar day of counters, used by the dashboard chart."""

    day: date
    created: int = 0
    completed: int = 0


class StatusSlice(BaseModel):
    status: TaskStatus
    count: int


class PrioritySlice(BaseModel):
    priority: Priority
    count: int


class MetricsResponse(BaseModel):
    overview: MetricsOverview
    tasks_by_status: list[StatusSlice] = []
    tasks_by_priority: list[PrioritySlice] = []
    activity_series: list[ActivityPoint] = []
    period_days: int = 30
