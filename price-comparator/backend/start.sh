#!/bin/bash
set -e

# Run migrations
alembic upgrade head

# Seed database (cria admin + 8 mercados)
python -m app.seeds || true

# Start Celery worker in background
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 &

# Start Celery beat in background
celery -A app.workers.celery_app beat --loglevel=info --scheduler celery.beat:PersistentScheduler &

# Aguarda worker iniciar, depois dispara crawl inicial se banco estiver vazio
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
        print(f'Banco já tem {count} produtos — coleta inicial não necessária.')

asyncio.run(check())
" || true) &

# Start FastAPI
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
