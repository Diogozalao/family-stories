"""Task-status polling endpoint + history management.

Clients start a background job by calling one of the ``/generate``
routes; those routes return a ``task_id`` immediately. The client then
polls this endpoint until ``state`` is ``done`` or ``failed``.

All endpoints filter ``task_records`` by ``user.id`` so a caller can
neither see nor cancel another user's jobs.
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.celery_app import celery_app
from backend.core.database import get_db
from backend.models.task import TaskRecord, TaskState

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
log    = structlog.get_logger()


def _serialize(record: TaskRecord) -> dict:
    return {
        "id":         record.id,
        "celery_id":  record.celery_id,
        "kind":       record.kind,
        "state":      record.state,
        "project_id": record.project_id,
        "story_id":   record.story_id,
        "video_id":   record.video_id,
        "payload":    record.payload,
        "result":     record.result,
        "error":      record.error,
        "created_at": str(record.created_at),
        "updated_at": str(record.updated_at),
    }


async def _get_owned(db: AsyncSession, task_id: int, user_id) -> TaskRecord:
    record = (await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id, TaskRecord.user_id == user_id)
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    return record


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Return the current state of one task — owner only."""
    record = await _get_owned(db, task_id, user.id)
    return _serialize(record)


@router.get("")
async def list_tasks(
    limit:      int        = 50,
    project_id: int | None = None,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    """Return the caller's most recent tasks.

    When ``project_id`` is given, only tasks of that project are returned,
    so each project sees its own tasks in isolation.
    """
    limit = max(1, min(limit, 200))
    stmt = select(TaskRecord).where(TaskRecord.user_id == user.id)
    if project_id is not None:
        stmt = stmt.where(TaskRecord.project_id == project_id)
    stmt = stmt.order_by(TaskRecord.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return [_serialize(r) for r in result.scalars().all()]


def _revoke_celery(celery_id: str | None) -> None:
    """Revoke a queued/running Celery task if one is associated."""
    if not celery_id:
        return
    try:
        celery_app.control.revoke(celery_id, terminate=True, signal="SIGTERM")
    except Exception as exc:                                # noqa: BLE001
        log.warning("celery_revoke_failed", celery_id=celery_id, error=str(exc))


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Stop a pending/running task. Keeps the row as ``failed`` — owner only."""
    record = await _get_owned(db, task_id, user.id)
    if record.state in (TaskState.DONE, TaskState.FAILED):
        return _serialize(record)

    _revoke_celery(record.celery_id)
    record.state      = TaskState.FAILED
    record.error      = "Cancelado pelo utilizador"
    record.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(record)
    log.info("task_cancelled", task_id=task_id, kind=record.kind.value)
    return _serialize(record)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Remove a task from history — owner only."""
    record = await _get_owned(db, task_id, user.id)

    if record.state in (TaskState.PENDING, TaskState.RUNNING):
        _revoke_celery(record.celery_id)

    await db.delete(record)
    await db.commit()
    log.info("task_deleted", task_id=task_id)


@router.delete("", status_code=204)
async def clear_finished_tasks(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Delete the caller's done/failed tasks at once. Active tasks untouched."""
    result = await db.execute(
        select(TaskRecord).where(
            TaskRecord.user_id == user.id,
            TaskRecord.state.in_([TaskState.DONE, TaskState.FAILED]),
        )
    )
    rows = result.scalars().all()
    for r in rows:
        await db.delete(r)
    await db.commit()
    log.info("tasks_cleared", count=len(rows))
