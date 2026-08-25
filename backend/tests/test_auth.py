"""Authentication rules: hashing, token issuance, rotation and revocation."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import RefreshToken, User


def test_password_is_hashed_not_stored_in_plaintext(
    client: TestClient, db_session: Session, user_payload: dict
) -> None:
    client.post("/api/v1/auth/register", json=user_payload)
    user = db_session.execute(select(User).where(User.email == user_payload["email"])).scalar_one()

    assert user.hashed_password != user_payload["password"]
    assert user.hashed_password.startswith("$2")
    assert verify_password(user_payload["password"], user.hashed_password)


def test_hashing_is_salted() -> None:
    assert hash_password("same-input") != hash_password("same-input")


def test_register_returns_tokens_and_user(client: TestClient, user_payload: dict) -> None:
    response = client.post("/api/v1/auth/register", json=user_payload)
    body = response.json()

    assert response.status_code == 201
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == user_payload["email"]
    assert "password" not in body["user"]
    assert "hashed_password" not in body["user"]


def test_register_rejects_duplicate_email(client: TestClient, user_payload: dict) -> None:
    client.post("/api/v1/auth/register", json=user_payload)
    response = client.post("/api/v1/auth/register", json=user_payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_normalises_email_case(client: TestClient, user_payload: dict) -> None:
    client.post("/api/v1/auth/register", json={**user_payload, "email": "ADA@Example.com"})
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": user_payload["password"]},
    )
    assert response.status_code == 200


def test_register_rejects_short_password(client: TestClient, user_payload: dict) -> None:
    response = client.post("/api/v1/auth/register", json={**user_payload, "password": "short"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_login_with_wrong_password_is_rejected(client: TestClient, user_payload: dict) -> None:
    client.post("/api/v1/auth/register", json=user_payload)
    response = client.post(
        "/api/v1/auth/login", json={"email": user_payload["email"], "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Incorrect email or password."


def test_login_for_unknown_email_gives_the_same_error(client: TestClient) -> None:
    """Identical message for both failures: the API does not confirm which emails exist."""
    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Incorrect email or password."


def test_protected_route_requires_a_token(client: TestClient) -> None:
    response = client.get("/api/v1/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_protected_route_rejects_a_forged_token(client: TestClient) -> None:
    response = client.get("/api/v1/projects", headers={"Authorization": "Bearer not.a.real.token"})
    assert response.status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(client: TestClient, auth: dict) -> None:
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {auth['refresh_token']}"}
    )
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client: TestClient, auth: dict) -> None:
    response = client.get("/api/v1/auth/me", headers=auth["headers"])

    assert response.status_code == 200
    assert response.json()["email"] == auth["user"]["email"]


def test_refresh_rotates_the_token_and_burns_the_old_one(client: TestClient, auth: dict) -> None:
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != auth["refresh_token"]

    replayed = client.post("/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]})
    assert replayed.status_code == 401


def test_logout_revokes_refresh_tokens(client: TestClient, db_session: Session, auth: dict) -> None:
    assert client.post("/api/v1/auth/logout", headers=auth["headers"]).status_code == 200

    stored = db_session.execute(select(RefreshToken)).scalars().all()
    assert stored and all(token.revoked_at is not None for token in stored)

    replayed = client.post("/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]})
    assert replayed.status_code == 401


def test_profile_update_changes_password(
    client: TestClient, auth: dict, user_payload: dict
) -> None:
    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "Ada L.", "password": "new-secure-password"},
        headers=auth["headers"],
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ada L."

    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": user_payload["email"], "password": "new-secure-password"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": user_payload["email"], "password": user_payload["password"]},
        ).status_code
        == 401
    )
