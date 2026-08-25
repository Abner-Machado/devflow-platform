"""Application configuration, loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Every value can be overridden by an environment variable."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- application ---
    PROJECT_NAME: str = "DevFlow API"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # --- database ---
    DATABASE_URL: str = "sqlite:///./devflow.db"
    SQL_ECHO: bool = False

    # --- security ---
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="HMAC key used to sign JWTs. Must be overridden outside development.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- seeding ---
    SEED_ON_STARTUP: bool = False

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list. `*` disables the allow-list entirely."""
        raw = self.CORS_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so the environment is read once per process."""
    return Settings()


settings = get_settings()
