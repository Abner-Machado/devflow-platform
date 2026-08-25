"""Development seed data.

Idempotent: running it twice leaves the database unchanged. Never enabled in
production - it is gated behind SEED_ON_STARTUP or run explicitly with
``python -m app.db.seed``.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.activity import Activity
from app.models.document import Document
from app.models.enums import ActivityAction, Priority, ProjectStatus, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.models.user import User

logger = get_logger(__name__)

DEMO_EMAIL = "demo@devflow.dev"
DEMO_PASSWORD = "demo12345"

PROJECTS: list[dict] = [
    {
        "name": "Payments Service",
        "description": "Billing and subscription API. Stripe integration, invoicing, dunning.",
        "status": ProjectStatus.ACTIVE,
        "priority": Priority.CRITICAL,
        "repository_url": "https://github.com/example/payments-service",
    },
    {
        "name": "Design System",
        "description": "Shared React component library and design tokens.",
        "status": ProjectStatus.ACTIVE,
        "priority": Priority.MEDIUM,
        "repository_url": None,
    },
    {
        "name": "Data Pipeline",
        "description": "Nightly ETL feeding the analytics warehouse.",
        "status": ProjectStatus.PLANNING,
        "priority": Priority.HIGH,
        "repository_url": None,
    },
    {
        "name": "Legacy Admin",
        "description": "Retired internal admin panel, kept for audit history.",
        "status": ProjectStatus.ARCHIVED,
        "priority": Priority.LOW,
        "repository_url": None,
    },
]

# (title, status, priority, days until due - negative means already overdue)
TASKS: dict[str, list[tuple[str, TaskStatus, Priority, int | None]]] = {
    "Payments Service": [
        ("Handle failed webhook retries", TaskStatus.IN_PROGRESS, Priority.CRITICAL, 3),
        ("Add idempotency keys to charge endpoint", TaskStatus.DONE, Priority.HIGH, None),
        ("Write dunning email templates", TaskStatus.TODO, Priority.MEDIUM, 9),
        ("Reconcile Stripe payouts nightly", TaskStatus.IN_REVIEW, Priority.HIGH, 1),
        ("Backfill invoice PDFs", TaskStatus.DONE, Priority.LOW, None),
        ("Rotate API credentials", TaskStatus.TODO, Priority.CRITICAL, -2),
    ],
    "Design System": [
        ("Publish v2 tokens to npm", TaskStatus.DONE, Priority.MEDIUM, None),
        ("Document the Button variants", TaskStatus.TODO, Priority.LOW, 14),
        ("Fix focus ring contrast on dark theme", TaskStatus.IN_PROGRESS, Priority.HIGH, 5),
        ("Drop deprecated Grid component", TaskStatus.TODO, Priority.LOW, None),
    ],
    "Data Pipeline": [
        ("Choose orchestration tool", TaskStatus.IN_REVIEW, Priority.HIGH, 7),
        ("Model the events schema", TaskStatus.TODO, Priority.MEDIUM, 12),
        ("Estimate warehouse cost", TaskStatus.DONE, Priority.MEDIUM, None),
    ],
    "Legacy Admin": [
        ("Export audit log to cold storage", TaskStatus.DONE, Priority.LOW, None),
    ],
}

DOCUMENTS: dict[str, list[tuple[str, str]]] = {
    "Payments Service": [
        (
            "Architecture overview",
            "# Architecture overview\n\n"
            "The payments service is a stateless FastAPI application backed by PostgreSQL.\n\n"
            "## Components\n\n"
            "- **API** - public REST surface, JWT authenticated.\n"
            "- **Worker** - consumes the webhook queue and retries with backoff.\n"
            "- **Ledger** - append-only table; balances are derived, never stored.\n\n"
            "## Invariants\n\n"
            "1. Every charge carries an idempotency key.\n"
            "2. A webhook is processed at least once and applied at most once.\n",
        ),
        (
            "Runbook: failed payouts",
            "# Runbook: failed payouts\n\n"
            "1. Check the payout_attempts table for the most recent failure reason.\n"
            "2. If the provider returned a 5xx, re-run scripts/retry_payout.py with the id.\n"
            "3. If the account is closed, mark the payout blocked and notify support.\n",
        ),
    ],
    "Design System": [
        (
            "Contribution guide",
            "# Contribution guide\n\n"
            "Every component ships with a story, a test and an accessibility note.\n\n"
            "- Use design tokens, never raw hex values.\n"
            "- Keyboard support is part of the definition of done.\n",
        ),
    ],
    "Data Pipeline": [
        (
            "Ingestion contract",
            "# Ingestion contract\n\n"
            "Producers publish newline-delimited JSON to the raw events bucket,\n"
            "partitioned by ingestion date.\n\n"
            "| Field | Type | Required |\n"
            "| --- | --- | --- |\n"
            "| event_id | uuid | yes |\n"
            "| occurred_at | timestamptz | yes |\n"
            "| payload | object | yes |\n",
        ),
    ],
}

_SUMMARIES = {
    ActivityAction.PROJECT_CREATED: "created project {title}",
    ActivityAction.TASK_CREATED: "created task {title}",
    ActivityAction.TASK_COMPLETED: "completed task {title}",
    ActivityAction.DOCUMENT_CREATED: "created document {title}",
}


def _log(
    db: Session,
    user: User,
    action: ActivityAction,
    title: str,
    project: Project | None,
    when: datetime,
) -> None:
    """Backdated activity row, so the dashboard chart has a real history."""
    db.add(
        Activity(
            action=action,
            entity_type=action.value.split("_")[0],
            entity_title=title,
            summary=_SUMMARIES[action].format(title=title),
            user_id=user.id,
            project_id=project.id if project else None,
            created_at=when,
        )
    )


def seed_database() -> None:
    """Populate a development database with a demo account and realistic content."""
    random.seed(7)  # deterministic output, so screenshots and demos stay stable
    now = datetime.now(UTC)

    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if existing is not None:
            logger.info("seed skipped: demo account already present")
            return

        user = User(
            email=DEMO_EMAIL,
            full_name="Demo Developer",
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.flush()

        for offset, spec in enumerate(PROJECTS):
            created = now - timedelta(days=25 - offset * 4)
            project = Project(owner_id=user.id, created_at=created, updated_at=created, **spec)
            db.add(project)
            db.flush()
            _log(db, user, ActivityAction.PROJECT_CREATED, project.name, project, created)

            for index, (title, status, priority, due_offset) in enumerate(
                TASKS.get(project.name, [])
            ):
                task_created = min(
                    created + timedelta(days=1 + index, hours=random.randint(0, 9)), now
                )
                completed_at = (
                    min(task_created + timedelta(days=random.randint(1, 4)), now)
                    if status == TaskStatus.DONE
                    else None
                )
                task = Task(
                    title=title,
                    description=f"Seeded task for {project.name}.",
                    status=status,
                    priority=priority,
                    due_date=now + timedelta(days=due_offset) if due_offset is not None else None,
                    completed_at=completed_at,
                    project_id=project.id,
                    assignee_id=user.id if index % 2 == 0 else None,
                    created_at=task_created,
                    updated_at=completed_at or task_created,
                )
                db.add(task)
                db.flush()
                _log(db, user, ActivityAction.TASK_CREATED, task.title, project, task_created)
                if completed_at is not None:
                    _log(db, user, ActivityAction.TASK_COMPLETED, task.title, project, completed_at)

            for index, (title, content) in enumerate(DOCUMENTS.get(project.name, [])):
                doc_created = min(created + timedelta(days=2 + index), now)
                document = Document(
                    title=title,
                    content=content,
                    project_id=project.id,
                    author_id=user.id,
                    created_at=doc_created,
                    updated_at=doc_created,
                )
                db.add(document)
                db.flush()
                _log(db, user, ActivityAction.DOCUMENT_CREATED, title, project, doc_created)

        db.commit()
        logger.info("seed complete: demo account %s / %s", DEMO_EMAIL, DEMO_PASSWORD)


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    configure_logging()
    seed_database()
