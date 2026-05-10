"""Celery tasks for M4 multimedia generation."""

from uuid import UUID

import structlog

from backend.core.celery_app import celery_app
from backend.core.database import AsyncSessionLocal
from backend.modules.m4_multimedia.processor import M4Processor
from backend.tasks._runtime import run_async, run_with_tracking

log = structlog.get_logger()


@celery_app.task(bind=True, name="video.generate")
def generate_video_task(self, task_record_id: int, story_id: int, user_id: str) -> dict:
    """Build the documentary video for ``story_id`` in the background.

    ``user_id`` is the UUID of the owner — the worker passes it through
    to the processor so the story/photo lookups remain scoped to the
    user that enqueued the job. Without this the worker would happily
    operate on someone else's story.
    """
    log.info("video_task_start", task_record_id=task_record_id, story_id=story_id, user_id=user_id)

    uid = UUID(user_id)

    async def _body() -> dict:
        async with AsyncSessionLocal() as session:
            processor = M4Processor()
            record    = await processor.generate_video(story_id, session, user_id=uid)
            return {
                "video_id":     record.id,
                "story_id":     story_id,
                "filename":     record.filename,
                "size_mb":      record.file_size_mb,
                "photos_used":  record.photos_used,
                "status":       record.status,
                "download_url": f"/api/v1/multimedia/video/{record.filename}"
                                 if record.filename else None,
            }

    return run_async(run_with_tracking(task_record_id, self.request.id, _body))
