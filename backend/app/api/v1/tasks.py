"""Task CRUD and filtering."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination, get_owned_project, get_owned_task
from app.core.exceptions import ValidationError
from app.models.enums import OPEN_TASK_STATUSES, ActivityAction, Priority, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.activity import record

router = APIRouter(prefix="/tasks", tags=["tasks"])

SORTABLE = {
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "due_date": Task.due_date,
    "title": Task.title,
    "priority": Task.priority,
    "status": Task.status,
}


def serialize_task(task: Task) -> TaskRead:
    item = TaskRead.model_validate(task)
    item.project_name = task.project.name if task.project else None
    return item


def _validate_assignee(db: DbSession, assignee_id: uuid.UUID | None) -> None:
    if assignee_id is None:
        return
    if db.get(User, assignee_id) is None:
        raise ValidationError("Assignee does not exist.")


@router.get("", response_model=Page[TaskRead], summary="List tasks with filters")
def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    pagination: Pagination,
    project_id: Annotated[uuid.UUID | None, Query(description="Restrict to one project.")] = None,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[Priority | None, Query()] = None,
    assignee_id: Annotated[uuid.UUID | None, Query()] = None,
    overdue: Annotated[
        bool | None, Query(description="Only unfinished tasks past their due date.")
    ] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    sort_by: Annotated[
        str, Query(description="One of: created_at, updated_at, due_date, title, priority, status.")
    ] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[TaskRead]:
    owned_projects = select(Project.id).where(Project.owner_id == current_user.id)
    filters = [Task.project_id.in_(owned_projects)]

    if project_id is not None:
        # Resolve through the ownership check so an unknown id 404s instead of
        # silently returning an empty page.
        get_owned_project(db, project_id, current_user)
        filters.append(Task.project_id == project_id)
    if status_filter is not None:
        filters.append(Task.status == status_filter)
    if priority is not None:
        filters.append(Task.priority == priority)
    if assignee_id is not None:
        filters.append(Task.assignee_id == assignee_id)
    if overdue:
        filters.extend(
            [
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_date.is_not(None),
                Task.due_date < datetime.now(UTC),
            ]
        )
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Task.title).like(pattern),
                func.lower(func.coalesce(Task.description, "")).like(pattern),
            )
        )

    total = int(
        db.execute(select(func.count()).select_from(Task).where(*filters)).scalar_one() or 0
    )
    column = SORTABLE.get(sort_by, Task.created_at)
    ordering = column.asc() if order == "asc" else column.desc()
    rows = (
        db.execute(
            select(Task)
            .where(*filters)
            .options(selectinload(Task.project), selectinload(Task.assignee))
            .order_by(ordering)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )
    return Page.build(
        [serialize_task(task) for task in rows], total, pagination.page, pagination.page_size
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: DbSession, current_user: CurrentUser) -> TaskRead:
    project = get_owned_project(db, payload.project_id, current_user)
    _validate_assignee(db, payload.assignee_id)

    task = Task(
        title=payload.title.strip(),
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        project_id=project.id,
        assignee_id=payload.assignee_id,
        completed_at=datetime.now(UTC) if payload.status == TaskStatus.DONE else None,
    )
    db.add(task)
    db.flush()

    record(
        db,
        user=current_user,
        action=ActivityAction.TASK_CREATED,
        entity_type="task",
        entity_title=task.title,
        entity_id=task.id,
        project_id=project.id,
    )
    if task.status == TaskStatus.DONE:
        record(
            db,
            user=current_user,
            action=ActivityAction.TASK_COMPLETED,
            entity_type="task",
            entity_title=task.title,
            entity_id=task.id,
            project_id=project.id,
        )
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> TaskRead:
    return serialize_task(get_owned_task(db, task_id, current_user))


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID, payload: TaskUpdate, db: DbSession, current_user: CurrentUser
) -> TaskRead:
    task = get_owned_task(db, task_id, current_user)
    changes = payload.model_dump(exclude_unset=True)

    if "project_id" in changes and changes["project_id"] is not None:
        get_owned_project(db, changes["project_id"], current_user)
    if "assignee_id" in changes:
        _validate_assignee(db, changes["assignee_id"])

    previous_status = task.status
    for field, value in changes.items():
        setattr(task, field, value)

    just_completed = previous_status != TaskStatus.DONE and task.status == TaskStatus.DONE
    if just_completed:
        task.completed_at = datetime.now(UTC)
    elif previous_status == TaskStatus.DONE and task.status != TaskStatus.DONE:
        # Reopened: clear the completion stamp so metrics stay truthful.
        task.completed_at = None

    if changes:
        record(
            db,
            user=current_user,
            action=ActivityAction.TASK_COMPLETED if just_completed else ActivityAction.TASK_UPDATED,
            entity_type="task",
            entity_title=task.title,
            entity_id=task.id,
            project_id=task.project_id,
        )
    db.commit()
    db.refresh(task)
    return serialize_task(task)


@router.delete("/{task_id}", response_model=Message)
def delete_task(task_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> Message:
    task = get_owned_task(db, task_id, current_user)
    title, project_id = task.title, task.project_id
    db.delete(task)
    db.flush()

    record(
        db,
        user=current_user,
        action=ActivityAction.TASK_DELETED,
        entity_type="task",
        entity_title=title,
        project_id=project_id,
    )
    db.commit()
    return Message(message=f"Task '{title}' deleted.")
