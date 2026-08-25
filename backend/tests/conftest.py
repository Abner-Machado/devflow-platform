"""Test fixtures.

By default every test runs against a private in-memory SQLite database created
from the SQLAlchemy metadata, so the suite needs no external service and leaves
no files behind. Setting TEST_DATABASE_URL points the same suite at a real
server - CI uses that to run everything a second time against PostgreSQL, which
is what keeps the two engines from quietly diverging.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import create_app
from app.models import Base

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture
def db_session() -> Iterator[Session]:
    if TEST_DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,  # one shared connection, so :memory: survives between calls
        )
    else:
        engine = create_engine(TEST_DATABASE_URL)

    # Drop first: a previous run that crashed mid-test can leave tables behind.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_payload() -> dict[str, str]:
    return {
        "email": "ada@example.com",
        "full_name": "Ada Lovelace",
        "password": "analytical-engine",
    }


@pytest.fixture
def auth(client: TestClient, user_payload: dict[str, str]) -> dict:
    """Register a user and return its tokens, headers and profile."""
    response = client.post("/api/v1/auth/register", json=user_payload)
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "refresh_token": body["refresh_token"],
        "user": body["user"],
    }


@pytest.fixture
def other_auth(client: TestClient) -> dict:
    """A second, unrelated account, used to prove tenant isolation."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "grace@example.com",
            "full_name": "Grace Hopper",
            "password": "nanoseconds-1906",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}, "user": body["user"]}


@pytest.fixture
def project(client: TestClient, auth: dict) -> dict:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Payments Service", "description": "Billing API", "priority": "high"},
        headers=auth["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()
