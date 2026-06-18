"""Helpers shared by all Celery task modules.

Celery workers run synchronously in their own processes and do not have
FastAPI's dependency injection. These helpers rebuild the minimal state
each task needs — an ``AsyncSession`` and a way to update the matching
``TaskRecord`` — without having to duplicate the boilerplate everywhere.
"""

import asyncio
from datetime import UTC, datetime
from typing import Awaitable, Callable, TypeVar

import structlog

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.logging import configure_logging
from backend.models.task import TaskRecord, TaskState

# Ensure logs from the worker follow the same format as the API.
configure_logging()
log = structlog.get_logger()

T = TypeVar("T")


def run_async(coro: Awaitable[T]) -> T:
    """Run ``coro`` on a fresh asyncio loop.

    Celery workers are synchronous processes; every task creates a short
    event loop to reuse the project's async data access layer.
    """
    return asyncio.run(coro)


async def mark_task_state(
    task_record_id: int,
    *,
    state:            TaskState,
    celery_id:        str | None = None,
    result:           dict       | None = None,
    error:            str        | None = None,
    skip_if_terminal: bool       = False,
) -> None:
    """Update one ``TaskRecord`` row with the latest worker state.

    When ``skip_if_terminal`` is set, the update is a no-op if the row is
    already ``done``/``failed`` — this stops a task that the user cancelled
    mid-run (marked ``failed``) from being resurrected to ``done`` when its
    background thread finally finishes.
    """
    async with AsyncSessionLocal() as session:
        record = await session.get(TaskRecord, task_record_id)
        if record is None:
            log.warning("task_record_missing", id=task_record_id)
            return
        if skip_if_terminal and record.state in (TaskState.DONE, TaskState.FAILED):
            log.info("task_state_skip_terminal", id=task_record_id, current=record.state.value)
            return
        record.state      = state
        record.updated_at = datetime.now(UTC)
        if celery_id is not None:
            record.celery_id = celery_id
        if result is not None:
            record.result = result
            # Deep-link the produced artifact so the UI's task toast can offer
            # an "Open" action straight to the story / video.
            if result.get("story_id") is not None:
                record.story_id = result["story_id"]
            if result.get("video_id") is not None:
                record.video_id = result["video_id"]
        if error is not None:
            record.error = error
        await session.commit()


async def run_with_tracking(
    task_record_id: int,
    celery_id:      str,
    coroutine_factory: Callable[[], Awaitable[dict]],
) -> dict:
    """Wrap a task body with state transitions + error capture.

    ``coroutine_factory`` returns a coroutine that performs the actual
    work and resolves to the dict we want to report back to the client.
    """
    await mark_task_state(task_record_id, state=TaskState.RUNNING, celery_id=celery_id)
    try:
        # Hard wall-clock cap on every task. The in-process executor has a
        # single worker, so one hung task (e.g. an LLM/network call with no
        # timeout of its own) would otherwise block every queued task forever
        # — exactly the "stuck on Pendente" symptom. Failing it here frees the
        # worker without needing a process restart.
        result = await asyncio.wait_for(coroutine_factory(), timeout=settings.TASK_MAX_SECONDS)
    except TimeoutError:
        msg = (f"A tarefa excedeu o tempo máximo ({settings.TASK_MAX_SECONDS}s) "
               "e foi terminada.")
        log.error("task_timeout", task_record_id=task_record_id,
                  limit=settings.TASK_MAX_SECONDS)
        await mark_task_state(task_record_id, state=TaskState.FAILED, error=msg,
                              skip_if_terminal=True)
        raise
    except Exception as exc:
        log.exception("task_failed", task_record_id=task_record_id, error=str(exc))
        await mark_task_state(task_record_id, state=TaskState.FAILED, error=str(exc),
                              skip_if_terminal=True)
        raise
    # ``skip_if_terminal`` so a user cancellation (FAILED) isn't overwritten.
    await mark_task_state(task_record_id, state=TaskState.DONE, result=result,
                          skip_if_terminal=True)
    return result
