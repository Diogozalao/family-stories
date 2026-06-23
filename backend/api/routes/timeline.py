"""Module 2 — Timeline + family graph routes (per-user).

Each endpoint filters by ``user.id`` and operates on the per-user
family graph snapshot in ``data/processed/graphs/{user_id}.json``.
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.database import get_db
from backend.models.timeline import TimelineEvent
from backend.modules.m2_temporal.processor import M2Processor

router = APIRouter(prefix="/api/v1", tags=["timeline"])
log    = structlog.get_logger()

processor = M2Processor()


@router.post("/timeline/build")
async def build_timeline(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Process the caller's M1 media and build/refresh their timeline."""
    result = await processor.process(db, user_id=user.id)
    return result


@router.get("/timeline")
async def get_timeline(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Return the caller's timeline, chronologically ordered."""
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.user_id == user.id)
        .order_by(TimelineEvent.sort_order)
    )
    events = result.scalars().all()

    return [
        {
            "id":            e.id,
            # Field names MUST match the frontend ``TimelineEvent`` type
            # (event_date / media_file_id). They used to be ``date`` /
            # ``media_id`` here, so every event arrived without a date
            # (grouped under "—") and never showed its photo.
            "event_date":    str(e.event_date) if e.event_date else None,
            "confidence":    e.date_confidence,
            "date_label":    e.date_label,
            "type":          e.event_type,
            "title":         e.title,
            "description":   e.description,
            "location":      e.location,
            "media_file_id": e.media_file_id,
            "person_ids":    e.person_ids,
        }
        for e in events
    ]


@router.get("/timeline/stats")
async def timeline_stats(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Stats on the caller's timeline — useful for the thesis report."""
    events_result = await db.execute(
        select(TimelineEvent).where(TimelineEvent.user_id == user.id)
    )
    events = events_result.scalars().all()

    by_type, by_year, by_conf = {}, {}, {}
    for e in events:
        t = e.event_type or "desconhecido"
        by_type[t] = by_type.get(t, 0) + 1
        if e.event_date:
            y = str(e.event_date.year)
            by_year[y] = by_year.get(y, 0) + 1
        c = str(e.date_confidence)
        by_conf[c] = by_conf.get(c, 0) + 1

    graph = processor._load_graph(user.id)
    return {
        "total_events":         len(events),
        "events_with_date":     sum(1 for e in events if e.event_date),
        "events_by_type":       by_type,
        "events_by_year":       by_year,
        "events_by_confidence": by_conf,
        "graph_stats":          graph.stats,
    }


@router.get("/family-graph")
async def get_family_graph(
    user: User = Depends(get_current_user),
):
    """Return the caller's family graph snapshot."""
    graph = processor._load_graph(user.id)
    return {
        "nodes": [
            {"id": n, **graph.graph.nodes[n]}
            for n in graph.graph.nodes
        ],
        "edges": [
            {"from": u, "to": v, **d}
            for u, v, d in graph.graph.edges(data=True)
        ],
        "summary": graph.get_narrative_summary(),
        "stats":   graph.stats,
    }
