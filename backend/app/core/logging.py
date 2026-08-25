"""Structured-ish application logging setup."""

import logging
import sys

from app.core.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging() -> None:
    """Configure the root logger once, at application start-up."""
    root = logging.getLogger()
    if root.handlers:
        # Uvicorn already installed handlers; only align the level.
        root.setLevel(settings.LOG_LEVEL.upper())
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL.upper())

    # SQLAlchemy is noisy at INFO when echo is on; keep it under our control.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.SQL_ECHO else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
