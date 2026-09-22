"""Unit tests for app.core.security.

These exercise the module directly, without going through the HTTP layer,
because the branches covered here (the 72-byte bcrypt boundary, a malformed
hash in the database, a token missing its subject claim) are cheap to hit
here and expensive to reach reliably through the API.
"""

import pytest
from jose import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.security import (
    MAX_PASSWORD_BYTES,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_accepts_password_at_the_byte_limit() -> None:
    password = "a" * MAX_PASSWORD_BYTES
    assert hash_password(password)


def test_hash_password_rejects_password_over_the_byte_limit() -> None:
    password = "a" * (MAX_PASSWORD_BYTES + 1)
    with pytest.raises(ValidationError):
        hash_password(password)


def test_hash_password_counts_utf8_bytes_not_characters() -> None:
    # Each "é" is 2 bytes in UTF-8, so 40 of them is 80 bytes: over the limit
    # even though len(password) == 40 characters.
    password = "é" * 40
    with pytest.raises(ValidationError):
        hash_password(password)


def test_verify_password_rejects_oversized_input_without_calling_bcrypt() -> None:
    # bcrypt itself would raise on input this long; verify_password must
    # short-circuit to False instead of letting that exception escape.
    oversized = "a" * (MAX_PASSWORD_BYTES + 1)
    assert verify_password(oversized, hash_password("normal-password")) is False


def test_verify_password_rejects_malformed_hash_instead_of_raising() -> None:
    # A row with a corrupted or non-bcrypt hash must fail the login, not 500.
    assert verify_password("whatever", "not-a-bcrypt-hash") is False


def test_decode_token_rejects_payload_without_subject() -> None:
    payload = {"type": "access", "jti": "x"}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(AuthenticationError):
        decode_token(token, "access")
