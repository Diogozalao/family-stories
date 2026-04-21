"""Module 4 — Multimedia generation routes.

Endpoints:
    POST   /api/v1/multimedia/generate/{story_id}  — build documentary
    GET    /api/v1/multimedia/video/{filename}     — download video
    GET    /api/v1/multimedia/videos               — list all videos
    GET    /api/v1/multimedia/status/{video_id}    — per-video status
    DELETE /api/v1/multimedia/videos/{video_id}    — remove from disk + DB
"""

from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.models.task import TaskKind, TaskRecord, TaskState
from backend.models.user import User
from backend.models.video import VideoOutput
from backend.modules.m4_multimedia.processor import M4Processor

router    = APIRouter(prefix="/api/v1/multimedia", tags=["multimedia"])
log       = structlog.get_logger()
processor = M4Processor()


@router.post("/generate/{story_id}")
@limiter.limit(settings.RATE_LIMIT_GENERATE)
async def generate_video(
    request:  Request,
    story_id: int,
    mode:     str          = Query("sync", regex="^(sync|background)$"),
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    """Build the documentary video for the given story.

    Takes between 1 and 5 minutes depending on photo count.
    ``mode=sync`` (default) blocks until the MP4 is on disk; the
    response contains the download URL. ``mode=background`` enqueues
    the job on Celery and returns a ``task_id`` that the client polls.
    """
    if mode == "sync":
        try:
            record = await processor.generate_video(story_id, db)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            log.error("m4_api_error", story_id=story_id, error=str(exc))
            raise HTTPException(status_code=500, detail=f"Video generation failed: {exc}")

        return {
            "message":      "Video generated successfully",
            "video_id":     record.id,
            "story_id":     story_id,
            "filename":     record.filename,
            "size_mb":      record.file_size_mb,
            "photos_used":  record.photos_used,
            "status":       record.status,
            "download_url": f"/api/v1/multimedia/video/{record.filename}",
        }

    task = TaskRecord(
        kind     = TaskKind.VIDEO,
        state    = TaskState.PENDING,
        story_id = story_id,
        payload  = {"story_id": story_id},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    from backend.tasks.video_tasks import generate_video_task
    async_result = generate_video_task.delay(task.id, story_id)
    task.celery_id = async_result.id
    await db.commit()

    log.info("video_task_enqueued", task_record_id=task.id, celery_id=async_result.id)
    return {
        "task_id":   task.id,
        "celery_id": async_result.id,
        "state":     task.state,
        "poll_url":  f"/api/v1/tasks/{task.id}",
    }


@router.get("/video/{filename}")
async def download_video(filename: str):
    """Stream the generated documentary MP4 back to the client."""
    # Block path-traversal attempts — only allow a plain filename component.
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    video_path = settings.PROCESSED_DIR / "videos" / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/videos")
async def list_videos(db: AsyncSession = Depends(get_db)):
    """Return every video record, newest first."""
    result = await db.execute(
        select(VideoOutput).order_by(VideoOutput.created_at.desc())
    )
    videos = result.scalars().all()
    return [
        {
            "id":           v.id,
            "story_id":     v.story_id,
            "filename":     v.filename,
            "size_mb":      v.file_size_mb,
            "photos_used":  v.photos_used,
            "status":       v.status,
            "created_at":   str(v.created_at),
            "download_url": f"/api/v1/multimedia/video/{v.filename}" if v.filename else None,
        }
        for v in videos
    ]


@router.get("/status/{video_id}")
async def video_status(video_id: int, db: AsyncSession = Depends(get_db)):
    """Return the status of a specific video by id."""
    video = await db.get(VideoOutput, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found")
    return {
        "id":            video.id,
        "story_id":      video.story_id,
        "status":        video.status,
        "filename":      video.filename,
        "size_mb":       video.file_size_mb,
        "error_message": video.error_message,
        "created_at":    str(video.created_at),
    }


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    """Delete a video from both disk and database."""
    video = await db.get(VideoOutput, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Not found")

    if video.file_path:
        disk_path = Path(video.file_path)
        if disk_path.exists():
            disk_path.unlink()

    await db.delete(video)
    await db.commit()
    return {"message": "Video deleted successfully"}
