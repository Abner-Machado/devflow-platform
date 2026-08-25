"""Application-level guarantees: health, schema, error envelope and migrations."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_is_generated(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"]
    assert "/api/v1/projects" in schema["paths"]
    assert "/api/v1/dashboard" in schema["paths"]


def test_unknown_route_uses_the_shared_error_envelope(client: TestClient) -> None:
    body = client.get("/api/v1/nope").json()

    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_validation_errors_name_the_offending_field(client: TestClient) -> None:
    body = client.post("/api/v1/auth/register", json={"email": "not-an-email"}).json()

    assert body["error"]["code"] == "validation_error"
    assert {detail["field"] for detail in body["error"]["details"]} >= {"email", "full_name"}


def test_cors_headers_are_returned_for_allowed_origins(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.slow
def test_migrations_build_the_same_schema_as_the_models(tmp_path: Path) -> None:
    """Runs Alembic end to end, then compares the result against the ORM metadata.

    This is what keeps `alembic upgrade head` honest: if a model changes without a
    migration, the table list stops matching and this test fails.
    """
    from app.models import Base

    database_path = tmp_path / "migrated.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(database_url)
    try:
        migrated_tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()

    assert migrated_tables == set(Base.metadata.tables)


@pytest.mark.slow
def test_seed_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.db import seed as seed_module
    from app.models import Base, Project, User

    engine = create_engine(f"sqlite:///{(tmp_path / 'seed.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(seed_module, "SessionLocal", factory)

    seed_module.seed_database()
    seed_module.seed_database()  # second run must be a no-op

    with factory() as session:
        assert session.query(User).count() == 1
        assert session.query(Project).count() == len(seed_module.PROJECTS)
    engine.dispose()
