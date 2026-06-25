"""Module 2 — Timeline + family graph routes (per-user).

Each endpoint filters by ``user.id`` and operates on the per-user
family graph snapshot in ``data/processed/graphs/{user_id}.json``.
"""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.database import get_db
from backend.models.timeline import Person, TimelineEvent
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
    project_id: int | None = Query(default=None, description="Project scope; omit for the global timeline"),
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Return the caller's timeline, chronologically ordered.

    Scoped to ``project_id`` (a project's own events, e.g. GEDCOM marriages
    and births imported into it) or the global timeline when omitted. This is
    what lets the project Timeline tab show the same genealogical events as
    the global one, just isolated to the project.
    """
    stmt = select(TimelineEvent).where(TimelineEvent.user_id == user.id)
    stmt = stmt.where(TimelineEvent.project_id == project_id) if project_id is not None \
        else stmt.where(TimelineEvent.project_id.is_(None))
    result = await db.execute(stmt.order_by(TimelineEvent.sort_order))
    events = result.scalars().all()

    # Persons in the SAME scope — used both to resolve who each stored event
    # is about AND to DERIVE birth/death events. The GEDCOM import only
    # persists marriages, so without this the timeline would never show
    # "Nascimento de ..." / "Falecimento de ..." that the user expects.
    pstmt = select(Person).where(Person.user_id == user.id)
    pstmt = pstmt.where(Person.project_id == project_id) if project_id is not None \
        else pstmt.where(Person.project_id.is_(None))
    persons = (await db.execute(pstmt)).scalars().all()
    people_by_id: dict[int, Person] = {p.id: p for p in persons}

    def _people(ids) -> list[str]:
        return [people_by_id[i].name for i in (ids or []) if i in people_by_id]

    def _family(ids) -> str | None:
        labels = {people_by_id[i].family_label for i in (ids or [])
                  if i in people_by_id and people_by_id[i].family_label}
        return ", ".join(sorted(labels)) if labels else None

    def _title(e) -> str:
        # Name the couple on a marriage instead of a bare "Casamento".
        if e.event_type == "casamento":
            ppl = _people(e.person_ids)
            if len(ppl) >= 2:
                return f"Casamento de {ppl[0]} e {ppl[1]}"
        return e.title

    # Field names MUST match the frontend ``TimelineEvent`` type
    # (event_date / media_file_id) — that mismatch once dropped every date.
    out: list[dict] = [
        {
            "id":            e.id,
            "event_date":    str(e.event_date) if e.event_date else None,
            "confidence":    e.date_confidence,
            "date_label":    e.date_label,
            "type":          e.event_type,
            "title":         _title(e),
            "description":   e.description,
            "location":      e.location,
            "media_file_id": e.media_file_id,
            "person_ids":    e.person_ids,
            "people":        _people(e.person_ids),
            "family":        _family(e.person_ids),
        }
        for e in events
    ]

    # Birth / death events derived from each person's dates. Negative,
    # namespaced ids never collide with real TimelineEvent (or photo) ids.
    for p in persons:
        if p.birth_date:
            out.append({
                "id":            -(p.id * 10 + 1),
                "event_date":    str(p.birth_date),
                "confidence":    None, "date_label": None,
                "type":          "nascimento",
                "title":         f"Nascimento de {p.name}",
                "description":   (f"em {p.birth_place}" if p.birth_place else None),
                "location":      p.birth_place,
                "media_file_id": None,
                "person_ids":    [p.id],
                "people":        [p.name],
                "family":        p.family_label,
            })
        if p.death_date:
            death_place = getattr(p, "death_place", None)
            out.append({
                "id":            -(p.id * 10 + 2),
                "event_date":    str(p.death_date),
                "confidence":    None, "date_label": None,
                "type":          "falecimento",
                "title":         f"Falecimento de {p.name}",
                "description":   (f"em {death_place}" if death_place else None),
                "location":      death_place,
                "media_file_id": None,
                "person_ids":    [p.id],
                "people":        [p.name],
                "family":        p.family_label,
            })

    # Chronological order (undated last). The frontend also groups by year.
    out.sort(key=lambda ev: ev["event_date"] or "9999-99-99")
    return out


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
