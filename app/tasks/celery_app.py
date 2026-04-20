"""Celery app + monthly beat schedule for auto-refresh tasks."""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "feasibility",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.data_refresh",
        "app.tasks.regulation_monitor",
        "app.tasks.comp_update",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Spec 5.3: monthly auto-refresh.
    beat_schedule={
        "feaso-data-refresh-monthly": {
            "task": "app.tasks.data_refresh.refresh_all_analyses",
            "schedule": crontab(hour=2, minute=15, day_of_month=1),
        },
        "feaso-regulation-monitor-monthly": {
            "task": "app.tasks.regulation_monitor.scan_for_changes",
            "schedule": crontab(hour=3, minute=30, day_of_month=1),
        },
        "feaso-comp-update-weekly": {
            "task": "app.tasks.comp_update.refresh_recent_comps",
            "schedule": crontab(hour=4, minute=0, day_of_week=1),  # Mondays
        },
    },
)
