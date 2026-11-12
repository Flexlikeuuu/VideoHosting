#!/usr/bin/env sh
set -e

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running Alembic migrations..."
    alembic upgrade head
fi

exec "$@"
