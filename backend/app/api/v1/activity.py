"""Read-only activity feed."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, Pagination, get_owned_project
from app.models.activity import Activity
from app.models.enums import ActivityAction
from app.schemas.activity import ActivityRead
from app.schemas.common import Page

router = APIRouter(prefix="/activity", tags=["activity"])


def serialize(activity: Activity) -> ActivityRead:
    item = ActivityRead.model_validate(activity)
    item.project_name = activity.project.name if activity.project else None
    return item


@router.get("", response_model=Page[ActivityRead], summary="Recent activity, newest first")
def list_activity(
    db: DbSession,
    current_user: CurrentUser,
    pagination: Pagination,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    action: Annotated[ActivityAction | None, Query(description="Filter by action type.")] = None,
) -> Page[ActivityRead]:
    filters = [Activity.user_id == current_user.id]
    if project_id is not None:
        get_owned_project(db, project_id, current_user)
        filters.append(Activity.project_id == project_id)
    if action is not None:
        filters.append(Activity.action == action)

    total = int(
        db.execute(select(func.count()).select_from(Activity).where(*filters)).scalar_one() or 0
    )
    rows = (
        db.execute(
            select(Activity)
            .where(*filters)
            .options(selectinload(Activity.project))
            .order_by(Activity.created_at.desc(), Activity.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )
    return Page.build(
        [serialize(activity) for activity in rows], total, pagination.page, pagination.page_size
    )
