"""Dashboard aggregate endpoint.

The landing screen needs five different slices; serving them in one response
keeps the first paint to a single round trip.
"""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.api.v1.activity import serialize as serialize_activity
from app.api.v1.projects import serialize_projects
from app.api.v1.tasks import serialize_task
from app.models.activity import Activity
from app.models.enums import ACTIVE_PROJECT_STATUSES, OPEN_TASK_STATUSES
from app.models.project import Project
from app.models.task import Task
from app.schemas.dashboard import DashboardResponse
from app.services import metrics as metrics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse, summary="Everything the dashboard renders")
def get_dashboard(
    db: DbSession,
    current_user: CurrentUser,
    activity_limit: Annotated[int, Query(ge=1, le=50)] = 8,
    project_limit: Annotated[int, Query(ge=1, le=20)] = 5,
    task_limit: Annotated[int, Query(ge=1, le=20)] = 6,
    days: Annotated[int, Query(ge=1, le=365)] = 14,
) -> DashboardResponse:
    active_projects = (
        db.execute(
            select(Project)
            .where(Project.owner_id == current_user.id, Project.status.in_(ACTIVE_PROJECT_STATUSES))
            .order_by(Project.updated_at.desc())
            .limit(project_limit)
        )
        .scalars()
        .all()
    )

    owned_projects = select(Project.id).where(Project.owner_id == current_user.id)
    upcoming_tasks = (
        db.execute(
            select(Task)
            .where(Task.project_id.in_(owned_projects), Task.status.in_(OPEN_TASK_STATUSES))
            .options(selectinload(Task.project), selectinload(Task.assignee))
            # Tasks with a deadline first, soonest at the top; undated ones follow.
            .order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.priority.desc())
            .limit(task_limit)
        )
        .scalars()
        .all()
    )

    recent_activity = (
        db.execute(
            select(Activity)
            .where(Activity.user_id == current_user.id)
            .options(selectinload(Activity.project))
            .order_by(Activity.created_at.desc(), Activity.id.desc())
            .limit(activity_limit)
        )
        .scalars()
        .all()
    )

    return DashboardResponse(
        overview=metrics_service.overview(db, current_user.id),
        recent_activity=[serialize_activity(activity) for activity in recent_activity],
        active_projects=serialize_projects(db, list(active_projects)),
        upcoming_tasks=[serialize_task(task) for task in upcoming_tasks],
        activity_series=metrics_service.activity_series(db, current_user.id, days),
    )
