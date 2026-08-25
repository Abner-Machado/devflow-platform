# API examples

Every example assumes the API is on `http://localhost:8000`. Responses are trimmed to the
interesting fields. The interactive reference is at `/docs`.

## Authentication

### Register

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Ada Lovelace", "email": "ada@example.com", "password": "analytical-engine"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": { "id": "0f2b...", "email": "ada@example.com", "full_name": "Ada Lovelace" }
}
```

### Log in and keep the token handy

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@devflow.dev", "password": "demo12345"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

Every call below uses it:

```bash
AUTH="Authorization: Bearer $TOKEN"
```

### Rotate an expiring access token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

The presented refresh token is revoked as the new pair is issued: replaying it returns `401`.

### Log out

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout -H "$AUTH"
```

Revokes every refresh token for the account. Access tokens are stateless and expire on their own.

## Projects

### Create

```bash
curl -X POST http://localhost:8000/api/v1/projects -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Payments Service",
        "description": "Billing and subscription API.",
        "status": "active",
        "priority": "critical",
        "repository_url": "https://github.com/acme/payments"
      }'
```

```json
{
  "id": "8f1c...",
  "name": "Payments Service",
  "status": "active",
  "priority": "critical",
  "stats": { "total_tasks": 0, "open_tasks": 0, "completed_tasks": 0, "document_count": 0, "progress": 0.0 }
}
```

`stats` is computed on every read, never stored.

### List, filter, search, sort, paginate

```bash
curl -G http://localhost:8000/api/v1/projects -H "$AUTH" \
  --data-urlencode "status=active" \
  --data-urlencode "priority=critical" \
  --data-urlencode "search=payments" \
  --data-urlencode "sort_by=updated_at" \
  --data-urlencode "order=desc" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=20"
```

```json
{ "items": [ ... ], "total": 1, "page": 1, "page_size": 20, "pages": 1 }
```

`sort_by` accepts `created_at`, `updated_at`, `name`, `priority`, `status`.

### Partial update

```bash
curl -X PATCH http://localhost:8000/api/v1/projects/8f1c... -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

Only the fields present in the body change; everything else is untouched.

### Delete

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/8f1c... -H "$AUTH"
```

Cascades to the project's tasks and documents.

## Tasks

### Create

```bash
curl -X POST http://localhost:8000/api/v1/tasks -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Handle failed webhook retries",
        "description": "Exponential backoff, dead-letter after five attempts.",
        "project_id": "8f1c...",
        "status": "in_progress",
        "priority": "critical",
        "due_date": "2026-09-30T17:00:00Z"
      }'
```

### Filters

```bash
# everything open and past its due date
curl -G http://localhost:8000/api/v1/tasks -H "$AUTH" --data-urlencode "overdue=true"

# one project, sorted by deadline
curl -G http://localhost:8000/api/v1/tasks -H "$AUTH" \
  --data-urlencode "project_id=8f1c..." \
  --data-urlencode "sort_by=due_date" \
  --data-urlencode "order=asc"

# by status and priority
curl -G http://localhost:8000/api/v1/tasks -H "$AUTH" \
  --data-urlencode "status=in_review" --data-urlencode "priority=high"
```

### Complete a task

```bash
curl -X PATCH http://localhost:8000/api/v1/tasks/3d9a... -H "$AUTH" \
  -H "Content-Type: application/json" -d '{"status": "done"}'
```

Sets `completed_at` and writes a `task_completed` activity. Moving the task back out of `done`
clears `completed_at` again, so the metrics stay truthful.

## Documentation

```bash
curl -X POST http://localhost:8000/api/v1/documents -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Architecture overview",
        "project_id": "8f1c...",
        "content": "# Architecture overview\n\nStateless API, append-only ledger.\n"
      }'

# search title and body
curl -G http://localhost:8000/api/v1/documents -H "$AUTH" --data-urlencode "search=ledger"
```

List responses carry an `excerpt` rather than the full body; fetch
`/api/v1/documents/{id}` for the Markdown itself.

## Activity

```bash
curl -G http://localhost:8000/api/v1/activity -H "$AUTH" \
  --data-urlencode "action=task_completed" --data-urlencode "page_size=10"
```

```json
{
  "items": [
    {
      "action": "task_completed",
      "entity_title": "Add idempotency keys to charge endpoint",
      "summary": "completed task Add idempotency keys to charge endpoint",
      "project_name": "Payments Service",
      "created_at": "2026-08-24T18:41:02Z"
    }
  ],
  "total": 5, "page": 1, "page_size": 10, "pages": 1
}
```

## Metrics and dashboard

```bash
curl http://localhost:8000/api/v1/metrics/overview -H "$AUTH"
```

```json
{
  "total_projects": 4,
  "active_projects": 3,
  "completed_projects": 0,
  "total_tasks": 14,
  "open_tasks": 9,
  "completed_tasks": 5,
  "overdue_tasks": 1,
  "total_documents": 4,
  "completion_rate": 35.7
}
```

```bash
# full report, including per-day series and the status/priority breakdowns
curl -G http://localhost:8000/api/v1/metrics -H "$AUTH" --data-urlencode "days=30"

# everything the dashboard screen renders, in one call
curl http://localhost:8000/api/v1/dashboard -H "$AUTH"
```

## Errors

Every failure has the same shape.

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" -d '{"email": "not-an-email"}'
```

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      { "field": "full_name", "message": "Field required", "type": "missing" },
      { "field": "email", "message": "value is not a valid email address", "type": "value_error" }
    ]
  }
}
```

| Status | `code`                 | When                                                   |
| ------ | ---------------------- | ------------------------------------------------------ |
| 401    | `authentication_error` | Missing, malformed, expired or revoked token           |
| 404    | `not_found`            | No such resource - **or** it belongs to another account |
| 409    | `conflict`             | Email already registered                               |
| 422    | `validation_error`     | Body or query parameters failed validation             |
| 500    | `internal_error`       | Unhandled failure; details are in the server log only  |
