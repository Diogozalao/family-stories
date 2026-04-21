"""Celery tasks for M3 narrative generation."""

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

    ``payload`` mirrors ``GenerateRequest`` — the route serializes it
    straight from the Pydantic model before enqueuing.
    """
    log.info("narrative_task_start", task_record_id=task_record_id, payload=payload)

    async def _body() -> dict:
        async with AsyncSessionLocal() as session:
            generator = NarrativeGenerator()
            story = await generator.generate(
                db         = session,
                title      = payload["title"],
                event_type = payload.get("event_type", "default"),
                query      = payload.get("query"),
                person_ids = payload.get("person_ids") or [],
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
