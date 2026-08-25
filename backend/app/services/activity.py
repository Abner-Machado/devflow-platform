"""Activity log writer.

Every mutating endpoint funnels through record() so the feed is produced by the
same code path that changes state, and can never drift from it.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.enums import ActivityAction
from app.models.user import User

_TEMPLATES: dict[ActivityAction, str] = {
    ActivityAction.PROJECT_CREATED: "created project {title}",
    ActivityAction.PROJECT_UPDATED: "updated project {title}",
    ActivityAction.PROJECT_DELETED: "deleted project {title}",
    ActivityAction.TASK_CREATED: "created task {title}",
    ActivityAction.TASK_UPDATED: "updated task {title}",
    ActivityAction.TASK_COMPLETED: "completed task {title}",
    ActivityAction.TASK_DELETED: "deleted task {title}",
    ActivityAction.DOCUMENT_CREATED: "created document {title}",
    ActivityAction.DOCUMENT_UPDATED: "updated document {title}",
    ActivityAction.DOCUMENT_DELETED: "deleted document {title}",
}

_ENTITY_TYPES: dict[str, str] = {
    "project": "project",
    "task": "task",
    "document": "document",
}


def record(
    db: Session,
    *,
    user: User,
    action: ActivityAction,
    entity_type: str,
    entity_title: str,
    entity_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> Activity:
    """Append one activity row. The caller owns the surrounding transaction."""
    if entity_type not in _ENTITY_TYPES:
        raise ValueError(f"Unknown activity entity type: {entity_type}")

    summary = _TEMPLATES[action].format(title=entity_title)
    activity = Activity(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_title=entity_title[:200],
        summary=summary[:400],
        user_id=user.id,
        project_id=project_id,
    )
    db.add(activity)
    return activity
