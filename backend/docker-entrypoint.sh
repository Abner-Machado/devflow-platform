#!/usr/bin/env sh
# Apply migrations before the API starts, then hand over to the CMD.
set -e

echo "[entrypoint] applying database migrations"
alembic upgrade head

if [ "${SEED_ON_STARTUP}" = "true" ]; then
  echo "[entrypoint] seeding development data"
  python -m app.db.seed
fi

echo "[entrypoint] starting: $*"
exec "$@"
