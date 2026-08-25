# Architecture

This document explains how DevFlow is put together and, where a choice was not obvious, why it was
made that way.

## Shape of the system

```
Browser ──HTTP──> nginx (frontend container) ──/api──> FastAPI (api container) ──> PostgreSQL
                     serves the built SPA
```

In development the nginx layer is absent: Vite serves the SPA on :5173 and proxies `/api`,
`/docs`, `/redoc`, `/openapi.json` and `/health` to the API on :8000. In production the browser
talks to a single origin, so no CORS grant is needed at all; the `CORS_ORIGINS` allow-list exists
for the development setup and for deployments that split the two hosts.

## Backend

### Layering

| Layer      | Responsibility                                                                |
| ---------- | ----------------------------------------------------------------------------- |
| `api/v1`   | HTTP: request shape, status codes, ownership checks, transaction boundaries.   |
| `services` | Logic shared between endpoints: the activity writer and metric aggregation.    |
| `models`   | The database schema.                                                          |
| `schemas`  | What crosses the wire, in both directions.                                     |
| `core`     | Cross-cutting: settings, logging, password hashing, JWT, error handling.       |

There is no repository layer. For CRUD this thin, one would be indirection without payoff:
SQLAlchemy's session already is the data-access abstraction, and each route reads as the query it
performs. Logic that *is* shared - activity logging, aggregation - lives in `services/`.

### Ownership and tenancy

Every project has an owner; tasks and documents inherit that owner through their project. The
dependency helpers `get_owned_project`, `get_owned_task` and `get_owned_document` are the single
gate: they raise `NotFoundError`, not `PermissionError`, when the row belongs to somebody else, so
the API never reveals that a resource exists. Every list endpoint filters through a subquery of
projects owned by the caller.

### Authentication

- Access tokens are short-lived (30 minutes by default) and **stateless**: verifying one is a
  signature check plus a user lookup, with no session table on the hot path.
- Refresh tokens are long-lived and **stateful**: each issued token's `jti` is stored in
  `refresh_tokens`. This is what makes logout real - it revokes the rows.
- `/auth/refresh` rotates: presenting a refresh token burns it and issues a new pair, so a stolen
  token stops working the moment the legitimate client refreshes.
- Login answers with one identical message for an unknown email and a wrong password, so the
  endpoint cannot be used to enumerate accounts.
- bcrypt hashes at most 72 bytes. Rather than silently truncating - which would make two different
  long passwords interchangeable - `hash_password` rejects anything longer, and the schema caps the
  field before it ever gets there.

### Derived data is never stored

Project progress, completion rate and every counter are computed at read time with SQL aggregates.
Nothing is denormalised into a column, so nothing can go stale, and no background job has to keep
it honest. `project_stats_map` batches the per-project counters into two grouped queries, so a page
of twenty projects costs three queries, not forty-one.

The one deliberate denormalisation is in `activities`: each row keeps `entity_title` and a rendered
`summary`. The referenced entity may be deleted later, and the feed still has to read correctly.

### Activity log

Every mutating endpoint calls `services.activity.record` inside the same transaction as the change
it describes. The log cannot disagree with the data, because a rollback takes both. Completion is
recorded only on the transition into `done` - a further edit of an already-finished task logs an
update, not a second completion, which is what keeps the "completed" series in the metrics honest.

### Enums and portability

Enum columns use `native_enum=False`, so they are `VARCHAR` with a `CHECK` constraint on both
PostgreSQL and SQLite. Adding a value later is a normal migration instead of a PostgreSQL
`ALTER TYPE` dance, and the same migration file runs on both engines. Primary keys are UUIDs via
SQLAlchemy's `Uuid` type: native on PostgreSQL, `CHAR(32)` on SQLite.

This portability is what lets the test suite run against in-memory SQLite with no service to boot,
while production runs PostgreSQL. Migrations are verified against both: a test runs
`alembic upgrade head` end to end and asserts the resulting schema matches the model metadata.

### Errors

`AppError` and its subclasses are the vocabulary; `register_exception_handlers` turns them - plus
validation failures, `HTTPException`s and anything unhandled - into one envelope:

```json
{ "error": { "code": "...", "message": "...", "details": [...] } }
```

Validation details name the offending field, which is what lets the frontend attach a message to
the right input instead of dumping a banner. No traceback ever reaches a client; unhandled
exceptions are logged with a stack trace and answered with a generic 500.

## Frontend

### State

Three kinds, kept apart:

- **Server state** - TanStack Query. Every mutation invalidates the query families whose numbers it
  could change (`DERIVED_KEYS`: dashboard, metrics, activity), so counters can never lag behind an
  edit made two screens away.
- **Session state** - one React context (`AuthProvider`) owns the user and the tokens.
- **Local UI state** - `useState`, in the component that renders it. Filters live in the page that
  shows them and are part of the query key, so the cache splits correctly per filter set.

No Redux, no global store: nothing here needs one.

### API client

`api/client.ts` is the only module that knows about tokens or the error envelope. It attaches the
bearer header, and on a 401 it refreshes once and replays the request. Concurrent 401s share a
single in-flight refresh, so a dashboard firing five requests at once produces one refresh, not
five. If the refresh fails, the stored tokens are cleared and the registered handler bounces the
user to `/login`.

### Design system

`styles/global.css` is the whole visual language: tokens first (colour, spacing, radius, type
scale, elevation), then the primitives that consume them. Components compose classes and never
invent a colour or a spacing value. Both themes are defined at the token layer only, so light and
dark stay consistent for free - the sole exception is the sign-in aside, which sits on a fixed dark
gradient in both themes and therefore uses literal light values for its text.

Every list and panel renders one of three states - loading skeleton, empty with a next action, or
an error with a retry - so a screen never shows a blank rectangle and never fails silently.

## Testing strategy

The suite is API-level rather than unit-level: tests drive the real routes through `TestClient`
against a real (SQLite) database. That covers the layers that actually break - serialisation,
authorisation, transactions, aggregation - and it survives refactors that would invalidate mocks.
The exceptions are the migration test and the seed-idempotency test, which shell out and touch the
filesystem, and are marked `slow`.

## Known limits

Deliberately out of scope for this version, and where they would go:

- **Multi-user projects.** The model has one owner per project. Collaboration needs a membership
  table and a role check in the ownership dependencies.
- **Refresh-token cleanup.** Revoked and expired rows accumulate; a periodic job should delete
  them.
- **Rate limiting.** `/auth/login` is unthrottled. In front of a real deployment that belongs at
  the reverse proxy, or as middleware backed by Redis.
- **Full-text search.** Search is `LIKE` over lowercased columns - fine at this size, and the point
  at which it stops being fine is the point to reach for PostgreSQL `tsvector`.
