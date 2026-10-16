#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ -n "$SEED_OFFICER_PASSWORD" ]; then
    echo "Seeding the officer login..."
    python -m loan_application.scripts.seed
else
    echo "SEED_OFFICER_PASSWORD not set - skipping the officer seed"
fi

exec "$@"
