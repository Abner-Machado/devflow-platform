"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1 import activity, auth, dashboard, documents, metrics, projects, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(tasks.router)
api_router.include_router(documents.router)
api_router.include_router(activity.router)
api_router.include_router(metrics.router)
