import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.models.timeline import TimelineEvent, Person
from backend.modules.m2_temporal.processor import M2Processor

router = APIRouter(prefix="/api/v1", tags=["timeline"])
log = structlog.get_logger()

processor = M2Processor()

@router.post("/timeline/build")
async def build_timeline(db: AsyncSession = Depends(get_db)):
    """
    Processa todos os media do M1 e constrói a timeline cronológica.
    Chama este endpoint depois de fazer uploads.
    """
    result = await processor.process(db)
    return result

@router.get("/timeline")
async def get_timeline(db: AsyncSession = Depends(get_db)):
    """Retorna a timeline completa ordenada cronologicamente."""
    result = await db.execute(
        select(TimelineEvent).order_by(TimelineEvent.sort_order)
    )
    events = result.scalars().all()

    return [
        {
            "id":          e.id,
            "date":        str(e.event_date) if e.event_date else None,
            "confidence":  e.date_confidence,
            "date_label":  e.date_label,
            "type":        e.event_type,
            "title":       e.title,
            "description": e.description,
            "location":    e.location,
            "media_id":    e.media_file_id,
            "person_ids":  e.person_ids,
        }
        for e in events
    ]

@router.get("/timeline/stats")
async def timeline_stats(db: AsyncSession = Depends(get_db)):
    """Estatísticas da timeline — útil para o relatório académico."""
    events_result = await db.execute(select(TimelineEvent))
    events = events_result.scalars().all()

    by_type  = {}
    by_year  = {}
    by_conf  = {}

    for e in events:
        # Por tipo
        t = e.event_type or "desconhecido"
        by_type[t] = by_type.get(t, 0) + 1

        # Por ano
        if e.event_date:
            y = str(e.event_date.year)
            by_year[y] = by_year.get(y, 0) + 1

        # Por confiança
        c = str(e.date_confidence)
        by_conf[c] = by_conf.get(c, 0) + 1

    return {
        "total_events":       len(events),
        "events_with_date":   sum(1 for e in events if e.event_date),
        "events_by_type":     by_type,
        "events_by_year":     by_year,
        "events_by_confidence": by_conf,
        "graph_stats":        processor.graph.stats,
    }

@router.get("/family-graph")
async def get_family_graph():
    """Retorna o grafo familiar em formato JSON."""
    import networkx as nx
    graph = processor.graph
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
