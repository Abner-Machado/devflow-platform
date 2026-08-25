"""Metrics derived from the caller's own data."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.metrics import MetricsOverview, MetricsResponse
from app.services import metrics as metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview, summary="Headline counters")
def get_overview(db: DbSession, current_user: CurrentUser) -> MetricsOverview:
    return metrics_service.overview(db, current_user.id)


@router.get("", response_model=MetricsResponse, summary="Full metric report")
def get_metrics(
    db: DbSession,
    current_user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=365, description="Length of the activity window.")] = 30,
) -> MetricsResponse:
    return metrics_service.full_report(db, current_user.id, days)
