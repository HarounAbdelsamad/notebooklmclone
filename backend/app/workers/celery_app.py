"""Celery application. Runs as a separate Render service from the API (same codebase)."""

from celery import Celery

from app.config import settings

celery = Celery(
    "notebooklm",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=15 * 60,
    task_soft_time_limit=13 * 60,
    worker_max_tasks_per_child=50,
)
