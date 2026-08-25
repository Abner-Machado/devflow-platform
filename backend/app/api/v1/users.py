"""Account settings for the authenticated user."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserRead, summary="Update the caller's profile")
def update_me(payload: UserUpdate, db: DbSession, current_user: CurrentUser) -> UserRead:
    changes = payload.model_dump(exclude_unset=True)
    if "full_name" in changes and changes["full_name"]:
        current_user.full_name = changes["full_name"].strip()
    if changes.get("password"):
        current_user.hashed_password = hash_password(changes["password"])
    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)
