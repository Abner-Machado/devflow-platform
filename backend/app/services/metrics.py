"""Aggregation helpers.

All figures come from SQL aggregates over the caller's own rows. Nothing here is
hardcoded or estimated: an empty account legitimately reports zeros.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.document import Document
from app.models.enums import (
    ACTIVE_PROJECT_STATUSES,
    OPEN_TASK_STATUSES,
    ActivityAction,
    Priority,
    ProjectStatus,
    TaskStatus,
)
from app.models.project import Project
from app.models.task import Task
from app.schemas.metrics import (
    ActivityPoint,
    MetricsOverview,
    MetricsResponse,
    PrioritySlice,
    StatusSlice,
)
from app.schemas.project import ProjectStats


def _owned_project_ids(owner_id: uuid.UUID) -> Select:
    return select(Project.id).where(Project.owner_id == owner_id)


def _scalar(db: Session, stmt: Select) -> int:
    return int(db.execute(stmt).scalar_one() or 0)


def project_stats_map(db: Session, project_ids: list[uuid.UUID]) -> dict[uuid.UUID, ProjectStats]:
    """Task/document counters for many projects in two queries (no N+1)."""
    stats: dict[uuid.UUID, ProjectStats] = {pid: ProjectStats() for pid in project_ids}
    if not project_ids:
        return stats

    task_rows = db.execute(
        select(Task.project_id, Task.status, func.count(Task.id))
        .where(Task.project_id.in_(project_ids))
        .group_by(Task.project_id, Task.status)
    ).all()
    for project_id, status, count in task_rows:
        entry = stats[project_id]
        entry.total_tasks += count
        if status == TaskStatus.DONE:
            entry.completed_tasks += count
        else:
            entry.open_tasks += count

    doc_rows = db.execute(
        select(Document.project_id, func.count(Document.id))
        .where(Document.project_id.in_(project_ids))
        .group_by(Document.project_id)
    ).all()
    for project_id, count in doc_rows:
        stats[project_id].document_count = count

    for entry in stats.values():
        entry.progress = (
            round(entry.completed_tasks / entry.total_tasks * 100, 1) if entry.total_tasks else 0.0
        )
    return stats


def overview(db: Session, owner_id: uuid.UUID) -> MetricsOverview:
    """Account-wide counters for the dashboard header."""
    owned = _owned_project_ids(owner_id)
    now = datetime.now(UTC)

    total_projects = _scalar(
        db, select(func.count()).select_from(Project).where(Project.owner_id == owner_id)
    )
    active_projects = _scalar(
        db,
        select(func.count())
        .select_from(Project)
        .where(Project.owner_id == owner_id, Project.status.in_(ACTIVE_PROJECT_STATUSES)),
    )
    completed_projects = _scalar(
        db,
        select(func.count())
        .select_from(Project)
        .where(Project.owner_id == owner_id, Project.status == ProjectStatus.COMPLETED),
    )
    total_tasks = _scalar(
        db, select(func.count()).select_from(Task).where(Task.project_id.in_(owned))
    )
    open_tasks = _scalar(
        db,
        select(func.count())
        .select_from(Task)
        .where(Task.project_id.in_(owned), Task.status.in_(OPEN_TASK_STATUSES)),
    )
    completed_tasks = _scalar(
        db,
        select(func.count())
        .select_from(Task)
        .where(Task.project_id.in_(owned), Task.status == TaskStatus.DONE),
    )
    overdue_tasks = _scalar(
        db,
        select(func.count())
        .select_from(Task)
        .where(
            Task.project_id.in_(owned),
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.due_date.is_not(None),
            Task.due_date < now,
        ),
    )
    total_documents = _scalar(
        db, select(func.count()).select_from(Document).where(Document.project_id.in_(owned))
    )

    return MetricsOverview(
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        total_tasks=total_tasks,
        open_tasks=open_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        total_documents=total_documents,
        completion_rate=round(completed_tasks / total_tasks * 100, 1) if total_tasks else 0.0,
    )


def _as_date(value: object) -> date | None:
    """SQLite returns an ISO string from date(); PostgreSQL returns a date object."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def activity_series(db: Session, owner_id: uuid.UUID, days: int = 30) -> list[ActivityPoint]:
    """Per-day created/completed counters over the requested window.

    Days with no activity are emitted as zeros so the chart has no gaps.
    """
    days = max(1, min(days, 365))
    start = datetime.now(UTC) - timedelta(days=days - 1)
    start_day = start.date()

    day_col = func.date(Activity.created_at)
    rows = db.execute(
        select(day_col, Activity.action, func.count(Activity.id))
        .where(Activity.user_id == owner_id, Activity.created_at >= start)
        .group_by(day_col, Activity.action)
    ).all()

    buckets: dict[date, ActivityPoint] = {
        start_day + timedelta(days=offset): ActivityPoint(day=start_day + timedelta(days=offset))
        for offset in range(days)
    }
    created_actions = {
        ActivityAction.PROJECT_CREATED,
        ActivityAction.TASK_CREATED,
        ActivityAction.DOCUMENT_CREATED,
    }
    for raw_day, action, count in rows:
        day = _as_date(raw_day)
        if day is None or day not in buckets:
            continue
        if action in created_actions:
            buckets[day].created += count
        elif action == ActivityAction.TASK_COMPLETED:
            buckets[day].completed += count

    return [buckets[key] for key in sorted(buckets)]


def full_report(db: Session, owner_id: uuid.UUID, days: int = 30) -> MetricsResponse:
    owned = _owned_project_ids(owner_id)

    status_rows = db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.project_id.in_(owned))
        .group_by(Task.status)
    ).all()
    status_counts = dict(status_rows)

    priority_rows = db.execute(
        select(Task.priority, func.count(Task.id))
        .where(Task.project_id.in_(owned))
        .group_by(Task.priority)
    ).all()
    priority_counts = dict(priority_rows)

    return MetricsResponse(
        overview=overview(db, owner_id),
        # Every enum member is emitted, including the empty ones, so the chart
        # keeps a stable set of series between refreshes.
        tasks_by_status=[
            StatusSlice(status=status, count=status_counts.get(status, 0)) for status in TaskStatus
        ],
        tasks_by_priority=[
            PrioritySlice(priority=priority, count=priority_counts.get(priority, 0))
            for priority in Priority
        ],
        activity_series=activity_series(db, owner_id, days),
        period_days=days,
    )
