"""Module 3 — Narrative generation routes."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.models.narrative import Story
from backend.models.task import TaskKind, TaskRecord, TaskState
from backend.models.user import User
from backend.modules.m3_narrative.generator import NarrativeGenerator
from backend.modules.m3_narrative.templates import NARRATIVE_TEMPLATES
from backend.schemas.narrative import GenerateRequest, StoryResponse

router    = APIRouter(prefix="/api/v1", tags=["narrative"])
log       = structlog.get_logger()
generator = NarrativeGenerator()


@router.post("/narrative/index")
async def index_facts(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Index every M1/M2 fact into the RAG system.

    Call this endpoint before generating narratives so the LLM has
    grounding context available.
    """
    result = await generator.index_all(db)
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
    """Generate a family narrative using LLM + RAG.

    ``mode=sync`` (default) blocks until the story is ready and returns
    the full ``StoryResponse``. ``mode=background`` enqueues the work
    on Celery, returns a ``task_id`` immediately, and the client polls
    ``GET /api/v1/tasks/{task_id}`` for progress.
    """
    if payload.event_type not in NARRATIVE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Available: {list(NARRATIVE_TEMPLATES.keys())}",
        )

    if mode == "sync":
        story = await generator.generate(
            db         = db,
            title      = payload.title,
            event_type = payload.event_type,
            query      = payload.query,
            person_ids = payload.person_ids,
        )
        return StoryResponse.model_validate(story)

    # Background mode — create a tracking record first, then enqueue.
    record = TaskRecord(
        kind    = TaskKind.NARRATIVE,
        state   = TaskState.PENDING,
        payload = payload.model_dump(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    from backend.tasks.narrative_tasks import generate_narrative_task
    async_result = generate_narrative_task.delay(record.id, payload.model_dump())
    record.celery_id = async_result.id
    await db.commit()

    log.info("narrative_task_enqueued", task_record_id=record.id, celery_id=async_result.id)
    return {
        "task_id":    record.id,
        "celery_id":  async_result.id,
        "state":      record.state,
        "poll_url":   f"/api/v1/tasks/{record.id}",
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
async def list_stories(db: AsyncSession = Depends(get_db)):
    """List every generated story, newest first."""
    result = await db.execute(select(Story).order_by(Story.created_at.desc()))
    return result.scalars().all()


@router.get("/narrative/stories/{story_id}", response_model=StoryResponse)
async def get_story(story_id: int, db: AsyncSession = Depends(get_db)):
    """Return a single story by id."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/narrative/stories/{story_id}")
async def delete_story(
    story_id: int,
    db:       AsyncSession = Depends(get_db),
    user:     User         = Depends(get_current_user),
):
    """Delete a story by id."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    await db.delete(story)
    await db.commit()
    return {"message": "Deleted successfully"}


@router.get("/narrative/rag/stats")
async def rag_stats():
    """Expose RAG statistics — handy for the thesis report."""
    return {
        "total_facts_indexed": generator.rag.total_facts,
        "llm_backend":         generator.llm.backend,
        "graph_persons":       len(generator.graph.graph.nodes),
        "graph_relations":     len(generator.graph.graph.edges),
    }
