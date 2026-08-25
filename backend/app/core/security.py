"""Password hashing and JWT creation/verification."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError

TokenType = Literal["access", "refresh"]

#: bcrypt hashes at most 72 bytes; anything longer is rejected instead of being
#: silently truncated, which would make two different passwords interchangeable.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt. Plaintext is never persisted."""
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValidationError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes when UTF-8 encoded."
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed hash in the database: a failed login, never a 500.
        return False


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """Return (encoded_token, jti, expires_at)."""
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti, expires_at


def create_access_token(subject: str) -> tuple[str, datetime]:
    token, _, expires_at = _create_token(
        subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return token, expires_at


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    """Refresh tokens carry a jti that is stored server-side, so logout can revoke them."""
    return _create_token(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:  # expired, bad signature, malformed
        raise AuthenticationError("Invalid or expired token.") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Expected a {expected_type} token.")
    if not payload.get("sub"):
        raise AuthenticationError("Token is missing a subject.")
    return payload
