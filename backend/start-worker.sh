#!/bin/bash

# Celery Worker Startup Script for Railway
# This script ensures proper security settings and environment setup

set -e

# Set environment variables if not already set
export PYTHONPATH="${PYTHONPATH:-/app}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://default:**@redis.railway.internal:6379//}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://default:**@redis.railway.internal:6379/}"

# Create a non-root user if running as root
if [ "$(id -u)" = "0" ]; then
    echo "Creating non-root user for Celery worker..."
    groupadd -r celery || true
    useradd -r -g celery celery || true
    chown -R celery:celery /app
    exec su-exec celery "$0" "$@"
fi

echo "Starting Celery worker with security settings..."
echo "User: $(id)"
echo "Broker: $CELERY_BROKER_URL"
echo "Backend: $CELERY_RESULT_BACKEND"

# Apply database migrations before starting worker
echo "Applying database migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head || {
        echo "WARNING: Failed to apply migrations. Worker will start anyway, but may encounter database errors."
    }
elif [ -f "/app/alembic.ini" ]; then
    python -m alembic upgrade head || {
        echo "WARNING: Failed to apply migrations. Worker will start anyway, but may encounter database errors."
    }
else
    echo "WARNING: Alembic not found. Skipping migrations. Ensure migrations are applied separately."
fi

# Start Celery worker with proper settings
exec celery -A app.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=1000 \
    --max-memory-per-child=200000 \
    --pool=prefork \
    -Q celery,analytics,telegram \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
