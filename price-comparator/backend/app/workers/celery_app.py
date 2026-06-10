from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "price_comparator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    beat_schedule={
        "refresh-prices-every-6h": {
            "task": "app.workers.tasks.refresh_all_prices",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    },
)
