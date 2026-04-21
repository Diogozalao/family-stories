"""Celery tasks for M4 multimedia generation."""

import structlog

from backend.core.celery_app import celery_app
from backend.core.database import AsyncSessionLocal
from backend.modules.m4_multimedia.processor import M4Processor
from backend.tasks._runtime import run_async, run_with_tracking

log = structlog.get_logger()


@celery_app.task(bind=True, name="video.generate")
def generate_video_task(self, task_record_id: int, story_id: int) -> dict:
    """Build the documentary video for ``story_id`` in the background."""
    log.info("video_task_start", task_record_id=task_record_id, story_id=story_id)

    async def _body() -> dict:
        async with AsyncSessionLocal() as session:
            processor = M4Processor()
            record    = await processor.generate_video(story_id, session)
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
