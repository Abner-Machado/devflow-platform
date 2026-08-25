"""Documentation module: CRUD, search and list-view shaping."""

from fastapi.testclient import TestClient

MARKDOWN = "# Architecture\n\nThe service is stateless and horizontally scalable.\n"


def _create(client: TestClient, auth: dict, project_id: str, **overrides) -> dict:
    payload = {"title": "Architecture", "content": MARKDOWN, "project_id": project_id, **overrides}
    response = client.post("/api/v1/documents", json=payload, headers=auth["headers"])
    assert response.status_code == 201, response.text
    return response.json()


def test_create_document_keeps_markdown_verbatim(
    client: TestClient, auth: dict, project: dict
) -> None:
    document = _create(client, auth, project["id"])

    assert document["content"] == MARKDOWN
    assert document["project_name"] == project["name"]
    assert document["author"]["email"] == auth["user"]["email"]


def test_list_returns_an_excerpt_instead_of_the_body(
    client: TestClient, auth: dict, project: dict
) -> None:
    """List responses stay small: the Markdown body is only sent on the detail route."""
    _create(client, auth, project["id"])

    item = client.get("/api/v1/documents", headers=auth["headers"]).json()["items"][0]

    # The excerpt skips the leading heading, which just repeats the title.
    assert item["excerpt"] == "The service is stateless and horizontally scalable."
    assert "content" not in item


def test_excerpt_falls_back_to_the_heading_for_a_title_only_document(
    client: TestClient, auth: dict, project: dict
) -> None:
    _create(client, auth, project["id"], title="Stub", content="# Just a heading")

    items = client.get("/api/v1/documents?search=stub", headers=auth["headers"]).json()["items"]

    assert items[0]["excerpt"] == "Just a heading"


def test_search_matches_title_and_body(client: TestClient, auth: dict, project: dict) -> None:
    _create(client, auth, project["id"])
    _create(client, auth, project["id"], title="Runbook", content="Restart the worker pool.")

    by_title = client.get("/api/v1/documents?search=runbook", headers=auth["headers"]).json()
    by_body = client.get("/api/v1/documents?search=stateless", headers=auth["headers"]).json()

    assert [item["title"] for item in by_title["items"]] == ["Runbook"]
    assert [item["title"] for item in by_body["items"]] == ["Architecture"]


def test_update_document(client: TestClient, auth: dict, project: dict) -> None:
    document = _create(client, auth, project["id"])

    updated = client.patch(
        f"/api/v1/documents/{document['id']}",
        json={"content": "# Rewritten\n"},
        headers=auth["headers"],
    ).json()

    assert updated["content"] == "# Rewritten\n"
    assert updated["title"] == "Architecture"


def test_delete_document(client: TestClient, auth: dict, project: dict) -> None:
    document = _create(client, auth, project["id"])

    assert (
        client.delete(f"/api/v1/documents/{document['id']}", headers=auth["headers"]).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/documents/{document['id']}", headers=auth["headers"]).status_code
        == 404
    )


def test_documents_are_scoped_to_their_owner(
    client: TestClient, auth: dict, other_auth: dict, project: dict
) -> None:
    document = _create(client, auth, project["id"])

    assert client.get("/api/v1/documents", headers=other_auth["headers"]).json()["total"] == 0
    assert (
        client.get(f"/api/v1/documents/{document['id']}", headers=other_auth["headers"]).status_code
        == 404
    )


def test_document_requires_an_owned_project(
    client: TestClient, other_auth: dict, project: dict
) -> None:
    response = client.post(
        "/api/v1/documents",
        json={"title": "Sneaky", "content": "", "project_id": project["id"]},
        headers=other_auth["headers"],
    )
    assert response.status_code == 404
