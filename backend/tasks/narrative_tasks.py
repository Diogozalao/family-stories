"""Celery task for M3 narrative generation.

The actual work lives in :func:`backend.tasks.bodies.narrative_body` so it
can be shared with the in-process executor used when no worker is running.
"""

import structlog

from backend.core.celery_app import celery_app
from backend.tasks._runtime import run_async, run_with_tracking
from backend.tasks.bodies import narrative_body

log = structlog.get_logger()


@celery_app.task(bind=True, name="narrative.generate")
def generate_narrative_task(self, task_record_id: int, payload: dict) -> dict:
    """Run the narrative body on a Celery worker, tracking task state."""
    log.info("narrative_task_start", task_record_id=task_record_id, payload=payload)
    return run_async(run_with_tracking(
        task_record_id, self.request.id, lambda: narrative_body(payload),
    ))
