"""Task-status polling endpoint.

Clients start a background job by calling one of the ``/generate``
routes; those routes return a ``task_id`` immediately. The client then
polls this endpoint until ``state`` is ``done`` or ``failed``.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.task import TaskRecord

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
log    = structlog.get_logger()


def _serialize(record: TaskRecord) -> dict:
    return {
        "id":         record.id,
        "celery_id":  record.celery_id,
        "kind":       record.kind,
        "state":      record.state,
        "story_id":   record.story_id,
        "video_id":   record.video_id,
        "payload":    record.payload,
        "result":     record.result,
        "error":      record.error,
        "created_at": str(record.created_at),
        "updated_at": str(record.updated_at),
    }


@router.get("/{task_id}")
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Return the current state of one task by id."""
    record = await db.get(TaskRecord, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(record)


@router.get("")
async def list_tasks(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Return the most recent tasks (for admin panels / debugging)."""
    limit = max(1, min(limit, 200))
    result = await db.execute(
        select(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit)
    )
    return [_serialize(r) for r in result.scalars().all()]
