# Development guide

## Requirements

| Tool           | Version | Needed for                          |
| -------------- | ------- | ----------------------------------- |
| Python         | 3.11+   | API (3.12 is what CI runs)          |
| Node.js        | 20+     | Frontend (22 in CI and Docker)      |
| Docker Compose | v2      | Optional: full stack with PostgreSQL |

PostgreSQL is optional locally - the API runs on SQLite when `DATABASE_URL` points at one.

## First run

```bash
git clone https://github.com/Abner-Machado/devflow-platform.git
cd devflow-platform
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into SECRET_KEY
```

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate            # Linux/macOS: . .venv/bin/activate
pip install -e ".[dev]"

export DATABASE_URL="sqlite:///./devflow.db"
export SECRET_KEY="local-dev-secret"

alembic upgrade head                # create the schema
python -m app.db.seed               # optional: demo account and content
uvicorn app.main:app --reload       # http://localhost:8000/docs
```

The seed is idempotent - running it twice changes nothing. It creates
`demo@devflow.dev` / `demo12345` with four projects, fourteen tasks, four documents and a
backdated activity history so the charts have something to draw.

### Frontend

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Vite proxies `/api`, `/docs`, `/redoc`, `/openapi.json` and `/health` to `http://localhost:8000`.
Point it elsewhere with `VITE_PROXY_TARGET`.

> On npm 12+, the first install may report that esbuild's install script was blocked. Run
> `npm install-scripts approve esbuild` once - Vite needs that binary to build.

## Everyday commands

```bash
# backend
pytest                              # whole suite
pytest -m "not slow"                # skip the subprocess/filesystem tests
pytest tests/test_metrics.py -k overdue -v
ruff check . --fix
ruff format .

# frontend
npm run dev
npm run lint
npm run typecheck
npm run build
```

## Database changes

1. Edit the model in `backend/app/models/`.
2. Generate the migration:
   ```bash
   cd backend
   alembic revision --autogenerate -m "add task estimate"
   ```
3. **Read the generated file.** Autogenerate is a first draft: it misses server defaults, data
   backfills and some constraint changes.
4. Apply and verify both directions:
   ```bash
   alembic upgrade head
   alembic downgrade -1 && alembic upgrade head
   ```
5. Run `pytest` - `test_migrations_build_the_same_schema_as_the_models` fails if the migration and
   the models have diverged.

`render_as_batch` is enabled for SQLite, which cannot `ALTER` most columns in place; Alembic
rewrites the table instead. Nothing extra is needed for PostgreSQL.

## Adding an endpoint

1. Schema in `app/schemas/` (separate `Create`, `Update` and `Read` models - update models are all
   optional, `PATCH` semantics).
2. Route module in `app/api/v1/`, registered in `router.py`.
3. Resolve ownership through `get_owned_*` before touching anything.
4. Call `services.activity.record` for anything that mutates state, in the same transaction.
5. Test it in `backend/tests/` - including the case where another account tries to reach it.
6. Frontend: add the type to `src/api/types.ts` and the hook to `src/api/hooks.ts`, invalidating
   the query families the mutation can affect.

## Conventions

**Backend.** Ruff (line length 100) for lint and formatting. Type hints everywhere. Comments
explain *why*, not what - the code already says what. `PATCH` bodies use `exclude_unset=True` so
"absent" and "explicitly null" stay distinguishable.

**Frontend.** ESLint with `typescript-eslint`, strict TypeScript. Components compose design-system
classes; no inline colours or spacing values. Every list renders loading, empty and error states.
Every interactive element is reachable by keyboard and has an accessible name.

**Commits.** Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`). One
logical change per commit.

## Docker

```bash
docker compose up --build           # api :8000, web :8080, db :5432
docker compose logs -f api
docker compose exec api alembic current
docker compose down -v              # also drops the database volume
```

The API container runs `alembic upgrade head` on start, then `uvicorn`; with
`SEED_ON_STARTUP=true` it seeds in between. It runs as an unprivileged user.

## Troubleshooting

| Symptom                                        | Cause and fix                                                            |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| `401` on every call right after signing in     | API restarted with a different `SECRET_KEY`; sign in again.               |
| Browser blocks requests with a CORS error      | Add the frontend origin to `CORS_ORIGINS`.                               |
| `alembic upgrade head` says "Can't locate revision" | The database was created by a different branch. `alembic downgrade base`, or drop the volume. |
| Frontend builds but the API 404s in Docker     | The browser must call `/api/v1` (nginx proxies it), not `localhost:8000`. |
| `vite build` fails on a missing esbuild binary | `npm install-scripts approve esbuild`.                                   |
