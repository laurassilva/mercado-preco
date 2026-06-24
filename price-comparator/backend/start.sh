#!/bin/bash
set -e

echo "=== Starting Price Comparator Backend ==="

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Seed database (cria admin + mercados)
echo "Seeding database..."
python -m app.seeds || true

# Start Celery only if Redis is reachable
if python -c "import redis; r = redis.from_url('${REDIS_URL:-redis://localhost:6379/0}'); r.ping(); print('Redis OK')" 2>/dev/null; then
    echo "Starting Celery worker..."
    celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 &

    echo "Starting Celery beat..."
    celery -A app.workers.celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler &

    # Dispara crawl inicial se banco estiver vazio
    (sleep 15 && python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, func
from app.core.config import settings
from app.models.product import MarketProduct
from app.workers.tasks import crawl_all_products

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        count = (await db.execute(select(func.count()).select_from(MarketProduct))).scalar() or 0
    await engine.dispose()
    if count < 100:
        print(f'Banco com apenas {count} produtos — disparando coleta inicial...')
        crawl_all_products.delay(None)
    else:
        print(f'Banco ja tem {count} produtos — coleta inicial nao necessaria.')

asyncio.run(check())
" || true) &
else
    echo "WARNING: Redis not reachable — Celery workers disabled (scraping will not run)"
fi

# Start FastAPI
echo "Starting uvicorn on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
