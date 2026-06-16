"""Module 3 — Narrative generation routes.

Every read/write is scoped to ``user.id`` because the backend connects
to Postgres as ``postgres`` (which bypasses RLS). The owner column on
``Story``/``TaskRecord`` plus the explicit ``WHERE user_id = ...`` is
what keeps a caller from accessing or mutating someone else's data.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.models.narrative import Story
from backend.models.task import TaskKind, TaskRecord, TaskState
from backend.modules.m3_narrative.generator import NarrativeGenerator
from backend.modules.m3_narrative.templates import NARRATIVE_TEMPLATES
from backend.schemas.narrative import GenerateRequest, StoryResponse, UpdateStoryRequest

router    = APIRouter(prefix="/api/v1", tags=["narrative"])
log       = structlog.get_logger()
generator = NarrativeGenerator()


@router.post("/narrative/index")
async def index_facts(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Reindex every M1/M2 fact owned by the caller into the RAG system."""
    result = await generator.index_all(db, user_id=user.id)
    return {"message": "Facts indexed successfully", **result}


@router.post("/narrative/generate")
@limiter.limit(settings.RATE_LIMIT_GENERATE)
async def generate_narrative(
    request: Request,
    payload: GenerateRequest,
    mode:    str          = Query("sync", regex="^(sync|background)$"),
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Generate a family narrative using LLM + RAG."""
    if payload.event_type not in NARRATIVE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Available: {list(NARRATIVE_TEMPLATES.keys())}",
        )

    if mode == "sync":
        try:
            story = await generator.generate(
                db               = db,
                user_id          = user.id,
                title            = payload.title,
                event_type       = payload.event_type,
                query            = payload.query,
                person_ids       = payload.person_ids,
                project_id       = payload.project_id,
                custom_tone      = payload.custom_tone,
                custom_structure = payload.custom_structure,
                language         = payload.language,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return StoryResponse.model_validate(story)

    # Background mode — create the tracking record first, then run the job
    # either on a Celery worker (if one exists) or in-process on this very
    # server (free cloud tier). Either way the request returns immediately
    # and the client polls /api/v1/tasks/{id}.
    job_payload = {**payload.model_dump(), "user_id": str(user.id)}
    record = TaskRecord(
        user_id    = user.id,
        kind       = TaskKind.NARRATIVE,
        state      = TaskState.PENDING,
        project_id = payload.project_id,
        payload    = job_payload,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    if settings.CELERY_ENABLED:
        from backend.tasks.narrative_tasks import generate_narrative_task
        celery_id = generate_narrative_task.delay(record.id, job_payload).id
        record.celery_id = celery_id
        await db.commit()
    else:
        from backend.tasks.bodies import narrative_body
        from backend.tasks.inproc import run_in_background
        celery_id = run_in_background(record.id, lambda: narrative_body(job_payload))

    log.info("narrative_task_enqueued", task_record_id=record.id,
             celery_id=celery_id, celery=settings.CELERY_ENABLED)
    return {
        "task_id":   record.id,
        "celery_id": celery_id,
        "state":     record.state,
        "poll_url":  f"/api/v1/tasks/{record.id}",
    }


@router.get("/narrative/templates")
async def list_templates():
    """Return the metadata for every narrative template."""
    return [
        {
            "id":        key,
            "name":      val["name"],
            "tone":      val["tone"],
            "structure": val["structure"],
        }
        for key, val in NARRATIVE_TEMPLATES.items()
    ]


@router.get("/narrative/stories", response_model=list[StoryResponse])
async def list_stories(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """List the caller's generated stories, newest first."""
    result = await db.execute(
        select(Story).where(Story.user_id == user.id).order_by(Story.created_at.desc())
    )
    return result.scalars().all()


@router.get("/narrative/stories/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: int,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    story = (await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.patch("/narrative/stories/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: int,
    payload:  UpdateStoryRequest,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    """Edit a generated story's title and/or narrative — owner only."""
    story = (await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    if payload.title is not None:
        title = payload.title.strip()
        if len(title) < 3:
            raise HTTPException(status_code=400, detail="Title must be at least 3 characters")
        story.title = title

    if payload.narrative is not None:
        narrative = payload.narrative.strip()
        if len(narrative) < 30:
            raise HTTPException(status_code=400, detail="Narrative must be at least 30 characters")
        story.narrative = narrative

    await db.commit()
    await db.refresh(story)
    log.info("story_updated", id=story.id, chars=len(story.narrative or ""))
    return story


@router.delete("/narrative/stories/{story_id}")
async def delete_story(
    story_id: int,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    story = (await db.execute(
        select(Story).where(Story.id == story_id, Story.user_id == user.id)
    )).scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    await db.delete(story)
    await db.commit()
    return {"message": "Deleted successfully"}


@router.get("/narrative/rag/stats")
async def rag_stats(
    user: User = Depends(get_current_user),
):
    """Stats restritas ao caller — não exposíamos contagens globais aos
    utilizadores por agora (até decidirmos se é informação útil)."""
    return {
        "facts_indexed_for_user": generator.rag.count_for(user.id),
        "llm_backend":            generator.llm.backend,
    }
