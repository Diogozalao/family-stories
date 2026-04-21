"""Celery application factory.

Workers are launched outside the FastAPI process::

    celery -A backend.core.celery_app worker --loglevel=info --concurrency=2

The FastAPI process imports this module only to enqueue tasks with
``.delay(...)`` or ``.apply_async(...)``; it does not itself execute
them.
"""

from celery import Celery

from backend.core.config import settings

celery_app = Celery(
    "family_stories",
    broker  = settings.REDIS_URL,
    backend = settings.REDIS_URL,
    include = [
        "backend.tasks.narrative_tasks",
        "backend.tasks.video_tasks",
    ],
)

celery_app.conf.update(
    task_serializer            = "json",
    result_serializer          = "json",
    accept_content             = ["json"],
    timezone                   = "UTC",
    enable_utc                 = True,
    task_track_started         = True,
    task_time_limit            = 60 * 30,   # 30 minutes hard timeout.
    task_soft_time_limit       = 60 * 25,   # Soft limit to give code time to clean up.
    worker_prefetch_multiplier = 1,         # Prevent one worker from hogging tasks.
    broker_connection_retry_on_startup = True,
)
