#!/bin/sh
set -eu

echo "Applying database migrations..."
alembic upgrade head

if [ "${BOOTSTRAP_ADMIN:-false}" = "true" ]; then
  echo "Bootstrapping initial roles, permissions, menus, and administrator..."
  python -m app.seed_data
fi

exec "$@"
