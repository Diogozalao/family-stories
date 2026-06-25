"""Module 4 — Multimedia generation routes.

Endpoints:
    POST   /api/v1/multimedia/generate/{story_id}  — build documentary
    GET    /api/v1/multimedia/video/{filename}     — download video
    GET    /api/v1/multimedia/videos               — list owned videos
    GET    /api/v1/multimedia/status/{video_id}    — per-video status
    DELETE /api/v1/multimedia/videos/{video_id}    — remove from disk + DB

Every row in ``video_outputs`` carries ``user_id``; every read here
filters by ``user.id`` so no caller can see/touch another user's videos.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user, get_current_user_query_or_header
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.core.supabase_storage import (
    cached_signed_url,
    delete_object,
    invalidate_signed_url,
)
from backend.models.narrative import Story
from backend.models.task import TaskKind, TaskRecord, TaskState
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
    """Build the documentary video for ``story_id`` (owned by caller).

    The client may ask for ``background`` (best for a local backend, which
    stays up for the whole render), but a cloud instance forces ``sync`` via
    ``VIDEO_FORCE_SYNC`` — there's no worker there and an in-process thread
    would be killed on sleep, stranding the video as "processing". This keeps
    the same "Gerar vídeo" button working in both environments.
    """
    if settings.VIDEO_FORCE_SYNC:
        mode = "sync"

    if mode == "sync":
        try:
            record = await processor.generate_video(story_id, db, user_id=user.id)
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

    # Herda o projeto da história, para que a tarefa de vídeo apareça no
    # mesmo projeto e não se misture com os outros.
    project_id = (await db.execute(
        select(Story.project_id).where(Story.id == story_id, Story.user_id == user.id)
    )).scalar_one_or_none()

    task = TaskRecord(
        user_id    = user.id,
        kind       = TaskKind.VIDEO,
        state      = TaskState.PENDING,
        story_id   = story_id,
        project_id = project_id,
        payload    = {"story_id": story_id, "user_id": str(user.id)},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Celery worker if available, otherwise run in-process on this server so
    # the free cloud tier still gets true background generation.
    if settings.CELERY_ENABLED:
        from backend.tasks.video_tasks import generate_video_task
        celery_id = generate_video_task.delay(task.id, story_id, str(user.id)).id
        task.celery_id = celery_id
        await db.commit()
    else:
        from backend.tasks.bodies import video_body
        from backend.tasks.inproc import run_in_background
        celery_id = run_in_background(task.id, lambda: video_body(story_id, user.id))

    log.info("video_task_enqueued", task_record_id=task.id,
             celery_id=celery_id, celery=settings.CELERY_ENABLED)
    return {
        "task_id":   task.id,
        "celery_id": celery_id,
        "state":     task.state,
        "poll_url":  f"/api/v1/tasks/{task.id}",
    }


@router.get("/video/{filename}")
async def download_video(
    filename: str,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user_query_or_header),
):
    """Redirect to a signed URL for the generated documentary MP4.

    Accepts JWT in header or ``?token=`` so ``<video>`` tags work. The
    lookup is by ``filename + user_id`` so a user can never download a
    video that doesn't belong to them even if they guess the filename.
    """
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    record = (await db.execute(
        select(VideoOutput).where(
            VideoOutput.filename == filename,
            VideoOutput.user_id  == user.id,
        )
    )).scalar_one_or_none()
    if not record or not record.file_path:
        raise HTTPException(status_code=404, detail="Video not found")

    signed = await cached_signed_url(record.file_path, expires_in=3600)
    return RedirectResponse(url=signed, status_code=302)


async def serialize_videos(db: AsyncSession, videos: list, user_id) -> list[dict]:
    """Serialise ``VideoOutput`` rows into the API shape used by the frontend.

    Shared by the global and the per-project video listings so both return
    the *same* fields (the project route used to leak raw ORM columns like
    ``file_size_mb`` and had no poster). The poster is the first photo of the
    story's first scene — a real frame instead of a grey rectangle.
    """
    story_ids = {v.story_id for v in videos if v.story_id}
    poster_by_story: dict[int, int] = {}
    if story_ids:
        rows = (await db.execute(
            select(Story.id, Story.scenes).where(
                Story.id.in_(story_ids), Story.user_id == user_id
            )
        )).all()
        for sid, scenes in rows:
            for sc in (scenes or []):
                pids = (sc or {}).get("photo_ids") or []
                if pids:
                    poster_by_story[sid] = pids[0]
                    break

    return [
        {
            "id":              v.id,
            "story_id":        v.story_id,
            "filename":        v.filename,
            "size_mb":         v.file_size_mb,
            "photos_used":     v.photos_used,
            "status":          v.status,
            "created_at":      str(v.created_at),
            "download_url":    f"/api/v1/multimedia/video/{v.filename}" if v.filename else None,
            "poster_media_id": poster_by_story.get(v.story_id),
        }
        for v in videos
    ]


@router.get("/videos")
async def list_videos(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Return every video record owned by the caller, newest first."""
    result = await db.execute(
        select(VideoOutput)
        .where(VideoOutput.user_id == user.id)
        .order_by(VideoOutput.created_at.desc())
    )
    return await serialize_videos(db, result.scalars().all(), user.id)


@router.get("/status/{video_id}")
async def video_status(
    video_id: int,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    """Return the status of a specific video by id — owner only."""
    video = (await db.execute(
        select(VideoOutput).where(VideoOutput.id == video_id, VideoOutput.user_id == user.id)
    )).scalar_one_or_none()
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
    """Delete a video from Supabase Storage and the database — owner only."""
    video = (await db.execute(
        select(VideoOutput).where(VideoOutput.id == video_id, VideoOutput.user_id == user.id)
    )).scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Not found")

    if video.file_path:
        invalidate_signed_url(video.file_path)
        try:
            await delete_object(video.file_path)
        except Exception as exc:
            log.warning("storage_delete_swallowed", key=video.file_path, error=str(exc))

    await db.delete(video)
    await db.commit()
    return {"message": "Video deleted successfully"}
