"""Genealogy routes — GEDCOM upload + per-user family graph access."""

import uuid
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import delete, select
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
    request: Request,
    file:    UploadFile = File(...),
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Import a GEDCOM file (from Ancestry, MyHeritage, etc.) for the caller."""
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in {".ged", ".gedcom"}:
        raise HTTPException(
            status_code=400,
            detail="File must have .ged or .gedcom extension",
        )

    validated = await validate_gedcom(file)

    # Per-user folder on disk so two users can never overwrite each other's
    # imported file.
    unique_name = f"{uuid.uuid4().hex}{validated.suffix}"
    dest_path   = settings.RAW_DIR / "gedcom" / str(user.id) / unique_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest_path, "wb") as fh:
        await fh.write(validated.content)

    log.info("gedcom_uploaded", filename=file.filename, size=validated.size, user_id=str(user.id))

    result = await gedcom_to_database(dest_path, db, user_id=user.id)

    return {
        "message":  "Family tree imported successfully",
        "filename": file.filename,
        **result,
    }


@router.get("/genealogy/persons")
async def list_persons(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Return every person imported from the caller's GEDCOM files."""
    result = await db.execute(
        select(Person).where(Person.user_id == user.id).order_by(Person.name)
    )
    persons = result.scalars().all()
    return [
        {
            "id":          p.id,
            "name":        p.name,
            "birth_date":  str(p.birth_date.date()) if p.birth_date else None,
            "birth_place": p.birth_place,
            "death_date":  str(p.death_date.date()) if p.death_date else None,
            "gedcom_id":   p.gedcom_id,
            "notes":       p.notes,
        }
        for p in persons
    ]


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
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Remove every imported person for the caller so a fresh GEDCOM can be loaded."""
    await db.execute(delete(Person).where(Person.user_id == user.id))
    await db.commit()

    graph_path = _user_graph_path(user.id)
    if graph_path.exists():
        graph_path.unlink()

    return {"message": "All persons removed"}
