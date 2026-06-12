"""Async task bodies shared by the Celery workers and the in-process executor.

These functions hold the *actual work* of a background job (run M3 / M4 and
return a small result dict). They are kept deliberately free of any Celery
import so they can also run inside the FastAPI process — see
:mod:`backend.tasks.inproc` — on hosts without a worker, such as the free
cloud tier where ``CELERY_ENABLED`` is false.
"""

from uuid import UUID

import structlog

from backend.core.database import AsyncSessionLocal
from backend.modules.m3_narrative.generator import NarrativeGenerator
from backend.modules.m4_multimedia.processor import M4Processor

log = structlog.get_logger()


async def narrative_body(payload: dict) -> dict:
    """Generate a story from a ``GenerateRequest``-shaped ``payload``.

    ``payload`` must carry ``user_id`` (the enqueuer injects it because a
    worker/thread has no HTTP context to decode the JWT itself).
    """
    user_id_raw = payload.get("user_id")
    if not user_id_raw:
        raise ValueError("narrative task payload missing user_id")
    user_id = UUID(user_id_raw)

    async with AsyncSessionLocal() as session:
        generator = NarrativeGenerator()
        story = await generator.generate(
            db               = session,
            user_id          = user_id,
            title            = payload["title"],
            event_type       = payload.get("event_type", "default"),
            query            = payload.get("query"),
            person_ids       = payload.get("person_ids") or [],
            project_id       = payload.get("project_id"),
            custom_tone      = payload.get("custom_tone"),
            custom_structure = payload.get("custom_structure"),
            language         = payload.get("language", "pt"),
        )
        return {
            "story_id":      story.id,
            "title":         story.title,
            "event_type":    story.event_type,
            "template_used": story.template_used,
            "llm_backend":   story.llm_backend,
            "facts_used":    story.facts_used,
            "chars":         len(story.narrative or ""),
        }


async def analyze_media_body(media_id: int, user_id: UUID) -> dict:
    """Run the deferred M1 AI analysis (Gemini/OCR) for one uploaded media."""
    from backend.modules.m1_ingestion.processor import M1Processor

    async with AsyncSessionLocal() as session:
        processor = M1Processor()
        record    = await processor.analyze(media_id, session, user_id=user_id)
        status    = getattr(record, "status", None)
        return {
            "media_id": media_id,
            "status":   status.value if hasattr(status, "value") else status,
        }


async def video_body(story_id: int, user_id: UUID) -> dict:
    """Build the documentary video for ``story_id`` owned by ``user_id``."""
    async with AsyncSessionLocal() as session:
        processor = M4Processor()
        record    = await processor.generate_video(story_id, session, user_id=user_id)
        return {
            "video_id":     record.id,
            "story_id":     story_id,
            "filename":     record.filename,
            "size_mb":      record.file_size_mb,
            "photos_used":  record.photos_used,
            "status":       record.status.value if hasattr(record.status, "value") else record.status,
            "download_url": f"/api/v1/multimedia/video/{record.filename}"
                             if record.filename else None,
        }
