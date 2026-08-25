"""Dashboard payload: one request, everything the landing screen needs."""

from pydantic import BaseModel

from app.schemas.activity import ActivityRead
from app.schemas.metrics import ActivityPoint, MetricsOverview
from app.schemas.project import ProjectRead
from app.schemas.task import TaskRead


class DashboardResponse(BaseModel):
    overview: MetricsOverview
    recent_activity: list[ActivityRead] = []
    active_projects: list[ProjectRead] = []
    upcoming_tasks: list[TaskRead] = []
    activity_series: list[ActivityPoint] = []
