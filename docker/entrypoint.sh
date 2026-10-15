#!/bin/sh
# Runs every time the api container starts:
# 1. bring the database schema up to date (safe to repeat)
# 2. create or reset the first officer, only if SEED_OFFICER_PASSWORD is set
# 3. start the server (the CMD from the Dockerfile)
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
