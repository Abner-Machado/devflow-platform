"""Registration, login, refresh and logout."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, TokenPair
from app.schemas.common import Message
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _issue_tokens(db: DbSession, user: User) -> TokenPair:
    access_token, _ = create_access_token(str(user.id))
    refresh_token, jti, refresh_expires = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=refresh_expires,
            created_at=datetime.now(UTC),
        )
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and sign in",
)
def register(payload: UserCreate, db: DbSession) -> AuthResponse:
    email = payload.email.lower().strip()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    tokens = _issue_tokens(db, user)
    db.commit()
    logger.info("user registered id=%s", user.id)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse, summary="Exchange credentials for tokens")
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    # Same message for unknown email and wrong password: no account enumeration.
    if user is None or not verify_password(payload.password, user.hashed_password):
        logger.info("failed login attempt for %s", email)
        raise AuthenticationError("Incorrect email or password.")
    if not user.is_active:
        raise AuthenticationError("User account is disabled.")

    tokens = _issue_tokens(db, user)
    db.commit()
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair, summary="Rotate an expiring access token")
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    claims = decode_token(payload.refresh_token, "refresh")
    stored = db.execute(
        select(RefreshToken).where(RefreshToken.jti == claims["jti"])
    ).scalar_one_or_none()

    if stored is None or stored.revoked_at is not None:
        raise AuthenticationError("Refresh token is no longer valid.")

    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("User account is unavailable.")

    # Rotation: the presented refresh token is burned as the new pair is issued.
    stored.revoked_at = datetime.now(UTC)
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


@router.post("/logout", response_model=Message, summary="Revoke the caller's refresh tokens")
def logout(db: DbSession, current_user: CurrentUser) -> Message:
    """Access tokens are stateless and expire on their own; refresh tokens are revoked here."""
    now = datetime.now(UTC)
    tokens = db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None)
        )
    ).scalars()
    for token in tokens:
        token.revoked_at = now
    db.commit()
    return Message(message="Signed out.")


@router.get("/me", response_model=UserRead, summary="Current authenticated user")
def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)
