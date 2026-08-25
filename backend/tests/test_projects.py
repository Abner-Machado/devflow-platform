"""Project CRUD, filtering and per-tenant isolation."""

import uuid

from fastapi.testclient import TestClient


def test_create_project_defaults(client: TestClient, auth: dict) -> None:
    response = client.post(
        "/api/v1/projects", json={"name": "Data Pipeline"}, headers=auth["headers"]
    )
    body = response.json()

    assert response.status_code == 201
    assert body["status"] == "planning"
    assert body["priority"] == "medium"
    assert body["stats"]["progress"] == 0.0
    assert body["owner_id"] == auth["user"]["id"]


def test_create_project_rejects_empty_name(client: TestClient, auth: dict) -> None:
    response = client.post("/api/v1/projects", json={"name": ""}, headers=auth["headers"])

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "name"


def test_create_project_rejects_malformed_repository_url(client: TestClient, auth: dict) -> None:
    response = client.post(
        "/api/v1/projects",
        json={"name": "Broken", "repository_url": "not-a-url"},
        headers=auth["headers"],
    )
    assert response.status_code == 422


def test_list_is_paginated(client: TestClient, auth: dict) -> None:
    for index in range(5):
        client.post("/api/v1/projects", json={"name": f"Project {index}"}, headers=auth["headers"])

    response = client.get("/api/v1/projects?page=2&page_size=2", headers=auth["headers"])
    body = response.json()

    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 2


def test_list_filters_by_status_and_priority(client: TestClient, auth: dict) -> None:
    client.post(
        "/api/v1/projects",
        json={"name": "Active one", "status": "active", "priority": "critical"},
        headers=auth["headers"],
    )
    client.post(
        "/api/v1/projects",
        json={"name": "Paused one", "status": "paused", "priority": "low"},
        headers=auth["headers"],
    )

    active = client.get("/api/v1/projects?status=active", headers=auth["headers"]).json()
    critical = client.get("/api/v1/projects?priority=critical", headers=auth["headers"]).json()

    assert [item["name"] for item in active["items"]] == ["Active one"]
    assert [item["name"] for item in critical["items"]] == ["Active one"]


def test_list_search_matches_name_and_description(client: TestClient, auth: dict) -> None:
    client.post(
        "/api/v1/projects",
        json={"name": "Billing", "description": "Handles invoices"},
        headers=auth["headers"],
    )
    client.post("/api/v1/projects", json={"name": "Website"}, headers=auth["headers"])

    by_name = client.get("/api/v1/projects?search=bill", headers=auth["headers"]).json()
    by_description = client.get("/api/v1/projects?search=INVOICE", headers=auth["headers"]).json()

    assert by_name["total"] == 1
    assert by_description["total"] == 1


def test_update_is_partial(client: TestClient, auth: dict, project: dict) -> None:
    response = client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"status": "active"},
        headers=auth["headers"],
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "active"
    assert body["name"] == project["name"]  # untouched field survives
    assert body["description"] == project["description"]


def test_update_rejects_an_unknown_status(client: TestClient, auth: dict, project: dict) -> None:
    response = client.patch(
        f"/api/v1/projects/{project['id']}", json={"status": "wat"}, headers=auth["headers"]
    )
    assert response.status_code == 422


def test_delete_cascades_to_tasks_and_documents(
    client: TestClient, auth: dict, project: dict
) -> None:
    client.post(
        "/api/v1/tasks",
        json={"title": "Doomed task", "project_id": project["id"]},
        headers=auth["headers"],
    )
    client.post(
        "/api/v1/documents",
        json={"title": "Doomed doc", "content": "# gone", "project_id": project["id"]},
        headers=auth["headers"],
    )

    assert (
        client.delete(f"/api/v1/projects/{project['id']}", headers=auth["headers"]).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/projects/{project['id']}", headers=auth["headers"]).status_code == 404
    )
    assert client.get("/api/v1/tasks", headers=auth["headers"]).json()["total"] == 0
    assert client.get("/api/v1/documents", headers=auth["headers"]).json()["total"] == 0


def test_unknown_project_returns_404(client: TestClient, auth: dict) -> None:
    response = client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth["headers"])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_another_users_project_is_invisible(
    client: TestClient, auth: dict, other_auth: dict, project: dict
) -> None:
    """Reported as missing rather than forbidden, so the API leaks no existence."""
    assert (
        client.get(f"/api/v1/projects/{project['id']}", headers=other_auth["headers"]).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "hijacked"},
            headers=other_auth["headers"],
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/projects/{project['id']}", headers=other_auth["headers"]
        ).status_code
        == 404
    )
    assert client.get("/api/v1/projects", headers=other_auth["headers"]).json()["total"] == 0


def test_project_stats_are_derived_from_tasks(
    client: TestClient, auth: dict, project: dict
) -> None:
    for status in ("done", "done", "todo", "in_progress"):
        client.post(
            "/api/v1/tasks",
            json={"title": f"task {status}", "project_id": project["id"], "status": status},
            headers=auth["headers"],
        )

    stats = client.get(f"/api/v1/projects/{project['id']}", headers=auth["headers"]).json()["stats"]

    assert stats["total_tasks"] == 4
    assert stats["completed_tasks"] == 2
    assert stats["open_tasks"] == 2
    assert stats["progress"] == 50.0
