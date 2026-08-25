"""Authentication schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds.")


class AuthResponse(TokenPair):
    """Token pair plus the authenticated user, so the client avoids a second call."""

    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)
