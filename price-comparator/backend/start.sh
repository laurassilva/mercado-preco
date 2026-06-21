#!/bin/bash
set -e

# Run migrations
alembic upgrade head

# Seed database
python -m app.seeds || true

# Start Celery worker in background
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 &

# Start Celery beat in background
celery -A app.workers.celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler &

# Start FastAPI
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
