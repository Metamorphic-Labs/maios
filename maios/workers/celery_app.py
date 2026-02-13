# maios/workers/celery_app.py
from celery import Celery
from celery.schedules import crontab

from maios.core.config import settings

app = Celery(
    "maios",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "maios.workers.tasks",
        "maios.workers.heartbeat",
    ],
)

# Configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    "heartbeat-check": {
        "task": "maios.workers.heartbeat.run_health_checks",
        "schedule": 300.0,  # Every 5 minutes
    },
    "daily-summary": {
        "task": "maios.workers.heartbeat.generate_daily_summary",
        "schedule": crontab(hour=9, minute=0),  # 9 AM UTC daily
    },
}
