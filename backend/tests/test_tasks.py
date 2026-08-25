"""Task lifecycle, filtering and the completion rules metrics depend on."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _create(client: TestClient, auth: dict, project_id: str, **overrides) -> dict:
    payload = {"title": "Ship it", "project_id": project_id, **overrides}
    response = client.post("/api/v1/tasks", json=payload, headers=auth["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def test_create_task_defaults(client: TestClient, auth: dict, project: dict) -> None:
    task = _create(client, auth, project["id"])

    assert task["status"] == "todo"
    assert task["priority"] == "medium"
    assert task["completed_at"] is None
    assert task["project_name"] == project["name"]


def test_task_requires_an_owned_project(
    client: TestClient, other_auth: dict, project: dict
) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={"title": "Sneaky", "project_id": project["id"]},
        headers=other_auth["headers"],
    )
    assert response.status_code == 404


def test_task_rejects_an_unknown_assignee(client: TestClient, auth: dict, project: dict) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={"title": "Orphan", "project_id": project["id"], "assignee_id": str(uuid.uuid4())},
        headers=auth["headers"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Assignee does not exist."


def test_completing_a_task_stamps_completed_at(
    client: TestClient, auth: dict, project: dict
) -> None:
    task = _create(client, auth, project["id"])
    updated = client.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "done"}, headers=auth["headers"]
    ).json()

    assert updated["status"] == "done"
    assert updated["completed_at"] is not None


def test_reopening_a_task_clears_completed_at(
    client: TestClient, auth: dict, project: dict
) -> None:
    task = _create(client, auth, project["id"], status="done")
    assert task["completed_at"] is not None

    reopened = client.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "in_progress"}, headers=auth["headers"]
    ).json()

    assert reopened["completed_at"] is None


def test_completion_is_recorded_once_in_the_activity_feed(
    client: TestClient, auth: dict, project: dict
) -> None:
    task = _create(client, auth, project["id"])
    client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"}, headers=auth["headers"])
    # A second write while already done must not log another completion.
    client.patch(f"/api/v1/tasks/{task['id']}", json={"priority": "high"}, headers=auth["headers"])

    feed = client.get("/api/v1/activity?action=task_completed", headers=auth["headers"]).json()
    assert feed["total"] == 1


def test_filters_narrow_the_result_set(client: TestClient, auth: dict, project: dict) -> None:
    _create(client, auth, project["id"], title="A todo")
    _create(client, auth, project["id"], title="A done", status="done")
    _create(client, auth, project["id"], title="Urgent", priority="critical")

    todo = client.get("/api/v1/tasks?status=todo", headers=auth["headers"]).json()
    critical = client.get("/api/v1/tasks?priority=critical", headers=auth["headers"]).json()
    searched = client.get("/api/v1/tasks?search=urg", headers=auth["headers"]).json()

    assert todo["total"] == 2
    assert critical["total"] == 1
    assert [item["title"] for item in searched["items"]] == ["Urgent"]


def test_overdue_filter_ignores_finished_work(
    client: TestClient, auth: dict, project: dict
) -> None:
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    _create(client, auth, project["id"], title="Late", due_date=past)
    _create(client, auth, project["id"], title="Late but done", due_date=past, status="done")
    _create(client, auth, project["id"], title="On time", due_date=future)

    overdue = client.get("/api/v1/tasks?overdue=true", headers=auth["headers"]).json()

    assert [item["title"] for item in overdue["items"]] == ["Late"]


def test_project_filter_validates_ownership(
    client: TestClient, other_auth: dict, project: dict
) -> None:
    response = client.get(
        f"/api/v1/tasks?project_id={project['id']}", headers=other_auth["headers"]
    )
    assert response.status_code == 404


def test_tasks_from_other_accounts_are_not_listed(
    client: TestClient, auth: dict, other_auth: dict, project: dict
) -> None:
    _create(client, auth, project["id"])

    assert client.get("/api/v1/tasks", headers=other_auth["headers"]).json()["total"] == 0


def test_sorting_by_due_date(client: TestClient, auth: dict, project: dict) -> None:
    soon = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    later = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    _create(client, auth, project["id"], title="Later", due_date=later)
    _create(client, auth, project["id"], title="Soon", due_date=soon)

    ordered = client.get("/api/v1/tasks?sort_by=due_date&order=asc", headers=auth["headers"]).json()

    assert [item["title"] for item in ordered["items"]] == ["Soon", "Later"]


def test_delete_removes_the_task(client: TestClient, auth: dict, project: dict) -> None:
    task = _create(client, auth, project["id"])

    assert client.delete(f"/api/v1/tasks/{task['id']}", headers=auth["headers"]).status_code == 200
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=auth["headers"]).status_code == 404
