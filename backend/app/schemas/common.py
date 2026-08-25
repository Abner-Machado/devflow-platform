"""Shared response envelopes."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Uniform pagination envelope used by every list endpoint."""

    items: list[T]
    total: int = Field(description="Total rows matching the filters, ignoring pagination.")
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0, description="Total number of pages for the current page size.")

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


class Message(BaseModel):
    """Simple acknowledgement body for endpoints with no resource to return."""

    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    """Documented shape of every error emitted by the API."""

    error: ErrorDetail
