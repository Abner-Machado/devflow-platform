#!/usr/bin/env bash
# One-shot local setup: virtualenv, dependencies, database, demo data, npm install.
# Run from anywhere: scripts/bootstrap.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
  # Replace the placeholder with a real key so the stack starts secure by default.
  python - "$SECRET" <<'PY'
import pathlib, sys
path = pathlib.Path(".env")
path.write_text(
    path.read_text(encoding="utf-8").replace(
        "SECRET_KEY=generate-a-random-value-before-running", f"SECRET_KEY={sys.argv[1]}"
    ),
    encoding="utf-8",
)
PY
  echo "[bootstrap] wrote .env with a generated SECRET_KEY"
fi

echo "[bootstrap] backend"
cd "$ROOT/backend"
python -m venv .venv 2>/dev/null || true
VENV_PY="$ROOT/backend/.venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="$ROOT/backend/.venv/Scripts/python.exe"

"$VENV_PY" -m pip install --upgrade pip >/dev/null
"$VENV_PY" -m pip install -e ".[dev]"

export DATABASE_URL="${DATABASE_URL:-sqlite:///./devflow.db}"
export SECRET_KEY="${SECRET_KEY:-local-dev-secret}"
"$VENV_PY" -m alembic upgrade head
"$VENV_PY" -m app.db.seed

echo "[bootstrap] frontend"
cd "$ROOT/frontend"
npm install

cat <<'MSG'

Done. Two terminals:

  cd backend  && .venv/bin/uvicorn app.main:app --reload    # Windows: .venv/Scripts/uvicorn.exe
  cd frontend && npm run dev

Then open http://localhost:5173 and sign in with demo@devflow.dev / demo12345
MSG
