"""In-process background execution for hosts without a Celery worker.

When ``CELERY_ENABLED`` is false (e.g. the free cloud tier, which can't
afford a separate worker process), the API still wants ``mode=background``
to return immediately and run the generation in the background — just
inside this same process instead of a dedicated worker.

Each task body runs on a small, bounded thread pool; every thread spins up
its own asyncio loop (exactly like a Celery worker does via
``run_async``), so the heavy work never blocks FastAPI's event loop and
the request can return a ``task_id`` straight away. The client then polls
``/api/v1/tasks/{id}`` just as it would for a real Celery job.

Trade-offs (acceptable for a single-tenant, free-tier deployment):
  * Bounded to one concurrent task to stay within ~512 MB of RAM; further
    tasks queue rather than run in parallel.
  * A task in flight does not survive a process restart — the lifespan
    orphan-sweep marks such rows as ``failed`` on the next boot.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, Callable
from uuid import uuid4

import structlog

from backend.tasks._runtime import run_async, run_with_tracking

log = structlog.get_logger()

# One worker on purpose: a video render alone is memory-heavy, and the free
# instance is tight on RAM. Tasks queue instead of running concurrently.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inproc-task")


def run_in_background(
    task_record_id: int,
    body_factory:   Callable[[], Awaitable[dict]],
) -> str:
    """Schedule ``body_factory`` to run in the background.

    Returns a synthetic id (stored on the ``TaskRecord`` as ``celery_id``)
    so the rest of the system can treat in-process jobs like Celery jobs.
    The state transitions (running → done/failed) are handled by
    :func:`run_with_tracking`, just like the Celery path.
    """
    synthetic_id = f"inproc-{uuid4().hex}"

    def _runner() -> None:
        try:
            run_async(run_with_tracking(task_record_id, synthetic_id, body_factory))
        except Exception:                       # already marked FAILED inside
            log.warning("inproc_task_errored", task_record_id=task_record_id)

    _EXECUTOR.submit(_runner)
    log.info("inproc_task_scheduled", task_record_id=task_record_id, id=synthetic_id)
    return synthetic_id
