"""Metrics and dashboard aggregates.

These assertions pin the numbers to what is actually in the database: an empty
account reports zeros, and every counter moves only when real rows change.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def test_empty_account_reports_zeros_not_placeholders(client: TestClient, auth: dict) -> None:
    overview = client.get("/api/v1/metrics/overview", headers=auth["headers"]).json()

    assert overview["total_projects"] == 0
    assert overview["total_tasks"] == 0
    assert overview["completion_rate"] == 0.0


def test_overview_counts_match_the_database(client: TestClient, auth: dict, project: dict) -> None:
    client.patch(
        f"/api/v1/projects/{project['id']}", json={"status": "active"}, headers=auth["headers"]
    )
    for status in ("done", "done", "done", "todo"):
        client.post(
            "/api/v1/tasks",
            json={"title": f"t-{status}", "project_id": project["id"], "status": status},
            headers=auth["headers"],
        )
    client.post(
        "/api/v1/documents",
        json={"title": "Doc", "content": "x", "project_id": project["id"]},
        headers=auth["headers"],
    )

    overview = client.get("/api/v1/metrics/overview", headers=auth["headers"]).json()

    assert overview["total_projects"] == 1
    assert overview["active_projects"] == 1
    assert overview["total_tasks"] == 4
    assert overview["completed_tasks"] == 3
    assert overview["open_tasks"] == 1
    assert overview["total_documents"] == 1
    assert overview["completion_rate"] == 75.0


def test_overdue_counter_only_counts_unfinished_work(
    client: TestClient, auth: dict, project: dict
) -> None:
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    client.post(
        "/api/v1/tasks",
        json={"title": "Late", "project_id": project["id"], "due_date": past},
        headers=auth["headers"],
    )
    client.post(
        "/api/v1/tasks",
        json={
            "title": "Late done",
            "project_id": project["id"],
            "due_date": past,
            "status": "done",
        },
        headers=auth["headers"],
    )

    overview = client.get("/api/v1/metrics/overview", headers=auth["headers"]).json()

    assert overview["overdue_tasks"] == 1


def test_metrics_are_isolated_per_account(
    client: TestClient, auth: dict, other_auth: dict, project: dict
) -> None:
    client.post(
        "/api/v1/tasks",
        json={"title": "Mine", "project_id": project["id"]},
        headers=auth["headers"],
    )

    other = client.get("/api/v1/metrics/overview", headers=other_auth["headers"]).json()

    assert other["total_tasks"] == 0
    assert other["total_projects"] == 0


def test_full_report_covers_every_enum_value(client: TestClient, auth: dict, project: dict) -> None:
    client.post(
        "/api/v1/tasks",
        json={"title": "Only one", "project_id": project["id"], "status": "in_review"},
        headers=auth["headers"],
    )

    report = client.get("/api/v1/metrics?days=7", headers=auth["headers"]).json()
    by_status = {slice_["status"]: slice_["count"] for slice_ in report["tasks_by_status"]}

    assert by_status == {"todo": 0, "in_progress": 0, "in_review": 1, "done": 0}
    assert len(report["tasks_by_priority"]) == 4
    assert report["period_days"] == 7


def test_activity_series_has_one_point_per_day(client: TestClient, auth: dict) -> None:
    report = client.get("/api/v1/metrics?days=14", headers=auth["headers"]).json()
    series = report["activity_series"]

    assert len(series) == 14
    assert series == sorted(series, key=lambda point: point["day"])


def test_activity_series_counts_todays_events(
    client: TestClient, auth: dict, project: dict
) -> None:
    task = client.post(
        "/api/v1/tasks",
        json={"title": "Today", "project_id": project["id"]},
        headers=auth["headers"],
    ).json()
    client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "done"}, headers=auth["headers"])

    series = client.get("/api/v1/metrics?days=2", headers=auth["headers"]).json()["activity_series"]
    today = series[-1]

    assert today["created"] >= 2  # the project and the task
    assert today["completed"] == 1


def test_dashboard_returns_every_section(client: TestClient, auth: dict, project: dict) -> None:
    client.patch(
        f"/api/v1/projects/{project['id']}", json={"status": "active"}, headers=auth["headers"]
    )
    client.post(
        "/api/v1/tasks",
        json={"title": "Visible", "project_id": project["id"]},
        headers=auth["headers"],
    )

    dashboard = client.get("/api/v1/dashboard", headers=auth["headers"]).json()

    assert dashboard["overview"]["total_tasks"] == 1
    assert [item["name"] for item in dashboard["active_projects"]] == [project["name"]]
    assert [item["title"] for item in dashboard["upcoming_tasks"]] == ["Visible"]
    assert dashboard["recent_activity"][0]["action"] == "task_created"
    assert dashboard["activity_series"]


def test_dashboard_excludes_archived_projects(
    client: TestClient, auth: dict, project: dict
) -> None:
    client.patch(
        f"/api/v1/projects/{project['id']}", json={"status": "archived"}, headers=auth["headers"]
    )

    dashboard = client.get("/api/v1/dashboard", headers=auth["headers"]).json()

    assert dashboard["active_projects"] == []
