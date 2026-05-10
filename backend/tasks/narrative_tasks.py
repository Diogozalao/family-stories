"""Celery tasks for M3 narrative generation."""

from uuid import UUID

import structlog

from backend.core.celery_app import celery_app
from backend.core.database import AsyncSessionLocal
from backend.modules.m3_narrative.generator import NarrativeGenerator
from backend.tasks._runtime import run_async, run_with_tracking

log = structlog.get_logger()


@celery_app.task(bind=True, name="narrative.generate")
def generate_narrative_task(
    self,
    task_record_id: int,
    payload:        dict,
) -> dict:
    """Run ``NarrativeGenerator.generate`` on a worker and persist the story.

    ``payload`` mirrors ``GenerateRequest`` plus the ``user_id`` injected
    by the enqueuer (the worker has no HTTP context so it cannot decode
    the JWT itself — the owning user must be passed in explicitly).
    """
    log.info("narrative_task_start", task_record_id=task_record_id, payload=payload)

    user_id_raw = payload.get("user_id")
    if not user_id_raw:
        raise ValueError("narrative task payload missing user_id")
    user_id = UUID(user_id_raw)

    async def _body() -> dict:
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

    return run_async(run_with_tracking(task_record_id, self.request.id, _body))
