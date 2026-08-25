# DevFlow

Projects, tasks, technical documentation, activity and delivery metrics for software teams -
in one panel, backed by one database.

DevFlow is a full-stack reference application: a FastAPI + PostgreSQL REST API with JWT
authentication and Alembic migrations, and a React + TypeScript single-page frontend. Every
number the interface shows is computed from the database; nothing on screen is hardcoded.

| Layer     | Stack                                                              |
| --------- | ------------------------------------------------------------------ |
| API       | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, JWT     |
| Database  | PostgreSQL 16 (SQLite supported for local runs and the test suite)  |
| Frontend  | React 18, TypeScript, Vite, React Router, TanStack Query, plain CSS |
| Packaging | Docker + Docker Compose, GitHub Actions CI                          |

---

## Features

- **Authentication** - registration, login, `/auth/me`, refresh-token rotation and a logout that
  actually revokes server-side. Passwords are hashed with bcrypt and never stored in plaintext.
- **Projects** - full CRUD with status, priority, repository link, filtering, search, sorting and
  pagination. Progress is derived from task counts, never stored.
- **Tasks** - full CRUD with status, priority, assignee, due date and an overdue filter.
  Completing a task stamps `completed_at`; reopening one clears it.
- **Documentation** - Markdown documents attached to a project, with full-text search over title
  and body, and a rendered preview.
- **Activity** - an append-only log written by the same code path that mutates state, so the feed
  can never drift from what happened.
- **Metrics** - completion rate, open/overdue counters, tasks by status and priority, and a daily
  activity series. All SQL aggregates over the caller's own rows.
- **Dashboard** - one endpoint returning every slice the landing screen needs, so first paint is a
  single round trip.

Each account only ever sees its own data: a resource owned by someone else is reported as missing
rather than forbidden, so the API never confirms that it exists.

---

## Quick start

### Option A - Docker (everything, including PostgreSQL)

```bash
cp .env.example .env
# set SECRET_KEY to a random value:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up --build
```

| Service          | URL                          |
| ---------------- | ---------------------------- |
| Frontend         | http://localhost:8080        |
| API              | http://localhost:8000        |
| API docs         | http://localhost:8000/docs   |

Migrations run automatically when the API container starts. Set `SEED_ON_STARTUP=true` in `.env`
to also load the demo dataset (`demo@devflow.dev` / `demo12345`).

### Option B - local, no Docker, no PostgreSQL

The API falls back to SQLite, so a local run needs nothing but Python and Node.

```bash
# --- API ---
cd backend
python -m venv .venv && . .venv/Scripts/activate     # Linux/macOS: . .venv/bin/activate
pip install -e ".[dev]"

export DATABASE_URL="sqlite:///./devflow.db"
export SECRET_KEY="local-dev-secret"
alembic upgrade head
python -m app.db.seed                                 # optional demo data
uvicorn app.main:app --reload
```

```bash
# --- frontend (second terminal) ---
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to localhost:8000
```

Sign in with `demo@devflow.dev` / `demo12345` if you seeded, or register a new account.

---

## Repository layout

```
backend/
  app/
    api/v1/        route handlers, one module per resource
    core/          config, logging, security, error handling
    db/            engine, session, seed data
    models/        SQLAlchemy models
    schemas/       Pydantic request/response models
    services/      activity log and metric aggregation
  alembic/         migrations
  tests/           pytest suite (63 tests)
frontend/
  src/
    api/           typed client, React Query hooks
    auth/          session context
    components/    design-system primitives, layout, forms
    pages/         one module per screen
    styles/        the whole design system, tokens first
docs/              architecture, development guide, API examples
.github/workflows/ CI
```

---

## Development

Common commands:

```bash
# backend
cd backend
pytest                    # 63 tests, SQLite in memory
ruff check . && ruff format --check .
alembic revision --autogenerate -m "describe change"
alembic upgrade head

# frontend
cd frontend
npm run dev
npm run lint
npm run build             # type-checks, then builds
```

More detail in [docs/development.md](docs/development.md). Design decisions and their reasoning
are in [docs/architecture.md](docs/architecture.md). Copy-pasteable request examples are in
[docs/api-examples.md](docs/api-examples.md).

---

## Configuration

Every setting is an environment variable; see [`.env.example`](.env.example) for the full list.
The ones that matter:

| Variable                      | Default                    | Purpose                                       |
| ----------------------------- | -------------------------- | --------------------------------------------- |
| `DATABASE_URL`                | `sqlite:///./devflow.db`   | SQLAlchemy URL. Use `postgresql+psycopg://...` |
| `SECRET_KEY`                  | -                          | JWT signing key. **Must** be set in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`                       | Access-token lifetime                          |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                        | Refresh-token lifetime                         |
| `CORS_ORIGINS`                | `http://localhost:5173`    | Comma-separated allow-list, or `*`             |
| `LOG_LEVEL`                   | `INFO`                     | Root log level                                 |
| `SEED_ON_STARTUP`             | `false`                    | Load demo data when the API boots              |
| `VITE_API_URL`                | `/api/v1`                  | Base URL the browser calls                     |

`.env` is git-ignored. No secret is committed to this repository.

---

## API

Interactive documentation is generated from the code and served at `/docs` (Swagger UI) and
`/redoc`. The OpenAPI schema itself is at `/openapi.json`.

| Method                | Path                        | Purpose                              |
| --------------------- | --------------------------- | ------------------------------------ |
| `POST`                | `/api/v1/auth/register`     | Create an account, receive tokens    |
| `POST`                | `/api/v1/auth/login`        | Exchange credentials for tokens      |
| `POST`                | `/api/v1/auth/refresh`      | Rotate an expiring access token      |
| `POST`                | `/api/v1/auth/logout`       | Revoke the caller's refresh tokens   |
| `GET`                 | `/api/v1/auth/me`           | Current user                         |
| `PATCH`               | `/api/v1/users/me`          | Update name or password              |
| `GET`                 | `/api/v1/dashboard`         | Everything the dashboard renders     |
| `GET/POST`            | `/api/v1/projects`          | List (filter, search, sort) / create |
| `GET/PATCH/DELETE`    | `/api/v1/projects/{id}`     | Read / partial update / delete       |
| `GET/POST`            | `/api/v1/tasks`             | List (filter, search, sort) / create |
| `GET/PATCH/DELETE`    | `/api/v1/tasks/{id}`        | Read / partial update / delete       |
| `GET/POST`            | `/api/v1/documents`         | List and search / create             |
| `GET/PATCH/DELETE`    | `/api/v1/documents/{id}`    | Read / partial update / delete       |
| `GET`                 | `/api/v1/activity`          | Activity feed                        |
| `GET`                 | `/api/v1/metrics`           | Full metric report                   |
| `GET`                 | `/api/v1/metrics/overview`  | Headline counters                    |
| `GET`                 | `/health`                   | Liveness probe                       |

Every failure uses the same envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [{ "field": "email", "message": "value is not a valid email address", "type": "value_error" }]
  }
}
```

---

## Tests and CI

`pytest` runs the whole API against an in-memory SQLite database - no external service required.
The suite covers password hashing, token rotation and revocation, tenant isolation, CRUD, filters,
the completion rules the metrics depend on, aggregate correctness, the error envelope, and a
migration test that asserts `alembic upgrade head` produces the same schema as the models.

GitHub Actions runs on every push and pull request: Ruff lint and format check, the backend suite
on SQLite, **the same suite again against a real PostgreSQL 16 service** (so the two engines cannot
quietly diverge), a migration up/down/up cycle, ESLint, a production frontend build, and a Docker
build of both images.

---

## Licence

[MIT](LICENSE).
