"""Genealogy routes — GEDCOM upload + per-user family graph access."""

import uuid
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import delete, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.core.upload_validator import validate_gedcom
from backend.models.timeline import Person
from backend.modules.m1_ingestion.gedcom_parser import gedcom_to_database

router = APIRouter(prefix="/api/v1", tags=["genealogy"])
log    = structlog.get_logger()


def _user_graph_path(user_id) -> Path:
    return settings.PROCESSED_DIR / "graphs" / f"{user_id}.json"


@router.post("/genealogy/upload")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_gedcom(
    request:      Request,
    file:         UploadFile = File(...),
    family_label: str | None = Form(default=None),
    db:           AsyncSession = Depends(get_db),
    user:         User         = Depends(get_current_user),
):
    """Import a GEDCOM file (from Ancestry, MyHeritage, etc.) for the caller.

    ``family_label`` is an optional free-form group name supplied by the
    user at upload time (e.g. "Dinis", "Nogueira"). All persons in this
    file are stamped with it so the Family page can split multiple trees
    into separate sections without merging them by surname.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in {".ged", ".gedcom"}:
        raise HTTPException(
            status_code=400,
            detail="File must have .ged or .gedcom extension",
        )

    validated = await validate_gedcom(file)

    unique_name = f"{uuid.uuid4().hex}{validated.suffix}"
    dest_path   = settings.RAW_DIR / "gedcom" / str(user.id) / unique_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest_path, "wb") as fh:
        await fh.write(validated.content)

    label = (family_label or "").strip() or None
    log.info("gedcom_uploaded", filename=file.filename, size=validated.size,
             user_id=str(user.id), family_label=label)

    result = await gedcom_to_database(dest_path, db, user_id=user.id, family_label=label)

    return {
        "message":      "Family tree imported successfully",
        "filename":     file.filename,
        "family_label": label,
        **result,
    }


@router.get("/genealogy/persons")
async def list_persons(
    family_label: str | None = Query(default=None, description="Optional filter by family group"),
    db:           AsyncSession = Depends(get_db),
    user:         User         = Depends(get_current_user),
):
    """Return every person imported from the caller's GEDCOM files.

    Optionally filtered by ``family_label`` to render a single tree at a
    time in the UI.
    """
    stmt = select(Person).where(Person.user_id == user.id)
    if family_label:
        stmt = stmt.where(Person.family_label == family_label)
    stmt = stmt.order_by(Person.family_label.nulls_last(), Person.name)

    persons = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id":           p.id,
            "name":         p.name,
            "birth_date":   str(p.birth_date.date()) if p.birth_date else None,
            "birth_place":  p.birth_place,
            "death_date":   str(p.death_date.date()) if p.death_date else None,
            "gedcom_id":    p.gedcom_id,
            "notes":        p.notes,
            "family_label": p.family_label,
        }
        for p in persons
    ]


@router.get("/genealogy/families")
async def list_families(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Return the distinct family labels owned by the caller, with counts.

    Powers the "tabs/chips" filter in the Family page that lets the user
    flip between trees imported from different GEDCOM files.
    """
    from sqlalchemy import func
    rows = (await db.execute(
        select(Person.family_label, func.count(Person.id))
        .where(Person.user_id == user.id)
        .group_by(Person.family_label)
        .order_by(Person.family_label.nulls_last())
    )).all()
    return [{"label": label, "count": count} for label, count in rows]


@router.get("/genealogy/persons/{person_id}")
async def get_person(
    person_id: int,
    db:        AsyncSession = Depends(get_db),
    user:      User         = Depends(get_current_user),
):
    """Return one person and their immediate relatives — owner only."""
    person = (await db.execute(
        select(Person).where(Person.id == person_id, Person.user_id == user.id)
    )).scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    from backend.modules.m2_temporal.family_graph import FamilyGraph
    graph = FamilyGraph()
    graph.load(_user_graph_path(user.id))
    context = graph.get_family_context(person_id)

    return {
        "id":          person.id,
        "name":        person.name,
        "birth_date":  str(person.birth_date.date()) if person.birth_date else None,
        "birth_place": person.birth_place,
        "death_date":  str(person.death_date.date()) if person.death_date else None,
        "gedcom_id":   person.gedcom_id,
        "notes":       person.notes,
        "relatives":   context.get("relatives", []),
    }


@router.get("/genealogy/graph")
async def get_graph(
    user: User = Depends(get_current_user),
):
    """Return the caller's complete family graph (for visualisation)."""
    from backend.modules.m2_temporal.family_graph import FamilyGraph
    graph = FamilyGraph()
    graph.load(_user_graph_path(user.id))

    return {
        "nodes":   [{"id": n, **graph.graph.nodes[n]} for n in graph.graph.nodes],
        "edges":   [{"from": u, "to": v, **d} for u, v, d in graph.graph.edges(data=True)],
        "summary": graph.get_narrative_summary(),
        "stats":   graph.stats,
    }


@router.delete("/genealogy/persons")
async def clear_persons(
    family_label: str | None = Query(default=None, description="Drop only this group; omit to wipe everything"),
    db:           AsyncSession = Depends(get_db),
    user:         User         = Depends(get_current_user),
):
    """Remove imported persons. Wipes only one tree if ``family_label`` is set."""
    stmt = delete(Person).where(Person.user_id == user.id)
    if family_label:
        stmt = stmt.where(Person.family_label == family_label)
    await db.execute(stmt)
    await db.commit()

    # If we wiped everything, also drop the cached graph file. When only
    # one label is wiped, we rebuild the graph lazily on next import.
    if not family_label:
        graph_path = _user_graph_path(user.id)
        if graph_path.exists():
            graph_path.unlink()

    return {"message": "Removed", "family_label": family_label}
