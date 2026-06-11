"""Celery task for M4 multimedia generation.

The actual work lives in :func:`backend.tasks.bodies.video_body` so it can
be shared with the in-process executor used when no worker is running.
"""

from uuid import UUID

import structlog

from backend.core.celery_app import celery_app
from backend.tasks._runtime import run_async, run_with_tracking
from backend.tasks.bodies import video_body

log = structlog.get_logger()


@celery_app.task(bind=True, name="video.generate")
def generate_video_task(self, task_record_id: int, story_id: int, user_id: str) -> dict:
    """Run the video body on a Celery worker, tracking task state."""
    log.info("video_task_start", task_record_id=task_record_id, story_id=story_id, user_id=user_id)
    uid = UUID(user_id)
    return run_async(run_with_tracking(
        task_record_id, self.request.id, lambda: video_body(story_id, uid),
    ))
