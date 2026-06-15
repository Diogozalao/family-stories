"""Genealogy routes — GEDCOM upload + per-user family graph access."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.core.upload_validator import validate_gedcom
from backend.models.timeline import Person, Relationship
from backend.modules.m1_ingestion.gedcom_parser import gedcom_to_database

ALLOWED_KINDS = {"pai", "mãe", "cônjuge"}


def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date string (``YYYY-MM-DD``) or return None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Data inválida: {raw} (usa AAAA-MM-DD).")


class PersonCreate(BaseModel):
    name:         str = Field(min_length=1, max_length=255)
    sex:          Optional[str] = None
    birth_date:   Optional[str] = None
    death_date:   Optional[str] = None
    birth_place:  Optional[str] = None
    notes:        Optional[str] = None
    family_label: Optional[str] = None


class PersonUpdate(BaseModel):
    name:         Optional[str] = None
    sex:          Optional[str] = None
    birth_date:   Optional[str] = None
    death_date:   Optional[str] = None
    birth_place:  Optional[str] = None
    notes:        Optional[str] = None
    family_label: Optional[str] = None


class RelationshipCreate(BaseModel):
    from_person_id: int
    to_person_id:   int
    kind:           str


class BulkPerson(BaseModel):
    ref:          str               # client-side temporary id
    name:         str
    sex:          Optional[str] = None
    birth_date:   Optional[str] = None
    death_date:   Optional[str] = None
    birth_place:  Optional[str] = None
    family_label: Optional[str] = None


class BulkRelationship(BaseModel):
    from_ref: str
    to_ref:   str
    kind:     str


class BulkTreeRequest(BaseModel):
    persons:       list[BulkPerson]       = []
    relationships: list[BulkRelationship] = []


def _person_dict(p: Person) -> dict:
    return {
        "id":           p.id,
        "name":         p.name,
        "sex":          p.sex,
        "birth_date":   str(p.birth_date.date()) if p.birth_date else None,
        "death_date":   str(p.death_date.date()) if p.death_date else None,
        "birth_place":  p.birth_place,
        "notes":        p.notes,
        "gedcom_id":    p.gedcom_id,
        "family_label": p.family_label,
    }


async def _rebuild_graph_from_db(db: AsyncSession, user_id) -> None:
    """Rewrite the on-disk narrative graph from the DB persons + relations.

    Called after any manual edit so the M3 narrative context stays in sync
    with what the user sees in the tree (the DB is the source of truth).

    Defensive on purpose: the graph is a *secondary* artefact (only the M3
    narrative reads it), so a failure to write it must never bubble up and
    fail the person/relationship edit the user actually asked for.
    """
    try:
        from backend.modules.m2_temporal.family_graph import FamilyGraph

        persons = (await db.execute(select(Person).where(Person.user_id == user_id))).scalars().all()
        rels    = (await db.execute(select(Relationship).where(Relationship.user_id == user_id))).scalars().all()

        graph = FamilyGraph()
        for p in persons:
            graph.add_person(p)
        for r in rels:
            graph.add_relation(r.from_person_id, r.to_person_id, r.kind)
            if r.kind in ("pai", "mãe"):
                graph.add_relation(r.to_person_id, r.from_person_id, "filho de")

        path = _user_graph_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)   # ephemeral disk may be empty
        graph.save(path)
    except Exception as exc:                              # never fail the edit
        log.warning("graph_rebuild_failed", error=str(exc))

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


# ── Manual person + relationship editing (tree builder) ─────────────────────

@router.post("/genealogy/persons", status_code=201)
async def create_person(
    payload: PersonCreate,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Create a person by hand (no GEDCOM needed)."""
    person = Person(
        user_id      = user.id,
        name         = payload.name.strip(),
        sex          = (payload.sex or None),
        birth_date   = _parse_date(payload.birth_date),
        death_date   = _parse_date(payload.death_date),
        birth_place  = (payload.birth_place or "").strip() or None,
        notes        = (payload.notes or "").strip() or None,
        family_label = (payload.family_label or "").strip() or None,
    )
    db.add(person)
    await db.commit()
    await db.refresh(person)
    await _rebuild_graph_from_db(db, user.id)
    log.info("person_created", id=person.id)
    return _person_dict(person)


@router.patch("/genealogy/persons/{person_id}")
async def update_person(
    person_id: int,
    payload:   PersonUpdate,
    db:        AsyncSession = Depends(get_db),
    user:      User         = Depends(get_current_user),
):
    """Edit a person's details — owner only."""
    person = (await db.execute(
        select(Person).where(Person.id == person_id, Person.user_id == user.id)
    )).scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")

    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields and (fields["name"] or "").strip():
        person.name = fields["name"].strip()
    if "sex" in fields:
        person.sex = (fields["sex"] or None)
    if "birth_date" in fields:
        person.birth_date = _parse_date(fields["birth_date"])
    if "death_date" in fields:
        person.death_date = _parse_date(fields["death_date"])
    if "birth_place" in fields:
        person.birth_place = (fields["birth_place"] or "").strip() or None
    if "notes" in fields:
        person.notes = (fields["notes"] or "").strip() or None
    if "family_label" in fields:
        person.family_label = (fields["family_label"] or "").strip() or None

    await db.commit()
    await db.refresh(person)
    await _rebuild_graph_from_db(db, user.id)
    log.info("person_updated", id=person.id)
    return _person_dict(person)


@router.delete("/genealogy/persons/{person_id}", status_code=204)
async def delete_person(
    person_id: int,
    db:        AsyncSession = Depends(get_db),
    user:      User         = Depends(get_current_user),
):
    """Delete a person (their relationships cascade) — owner only."""
    person = (await db.execute(
        select(Person).where(Person.id == person_id, Person.user_id == user.id)
    )).scalar_one_or_none()
    if not person:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")
    await db.delete(person)
    await db.commit()
    await _rebuild_graph_from_db(db, user.id)
    log.info("person_deleted", id=person_id)


@router.get("/genealogy/tree")
async def get_tree(
    family_label: Optional[str] = Query(default=None),
    db:           AsyncSession  = Depends(get_db),
    user:         User          = Depends(get_current_user),
):
    """Return persons + relationships for the interactive tree / editor."""
    pstmt = select(Person).where(Person.user_id == user.id)
    if family_label:
        pstmt = pstmt.where(Person.family_label == family_label)
    persons = (await db.execute(pstmt.order_by(Person.name))).scalars().all()
    person_ids = {p.id for p in persons}

    rels = (await db.execute(
        select(Relationship).where(Relationship.user_id == user.id)
    )).scalars().all()
    relationships = [
        {"id": r.id, "from": r.from_person_id, "to": r.to_person_id, "kind": r.kind}
        for r in rels
        if r.from_person_id in person_ids and r.to_person_id in person_ids
    ]
    return {"persons": [_person_dict(p) for p in persons], "relationships": relationships}


@router.post("/genealogy/tree/bulk", status_code=201)
async def bulk_tree(
    payload: BulkTreeRequest,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Create several persons and relationships in a single transaction.

    Used by the pedigree wizard so building a whole family is one atomic,
    retry-safe request (instead of dozens of calls that a cold start could
    drop mid-way). Relationships reference persons by their client-side
    ``ref``; only links between two created persons are kept.
    """
    ref_to_id: dict[str, int] = {}
    for bp in payload.persons:
        if not bp.name.strip():
            continue
        person = Person(
            user_id      = user.id,
            name         = bp.name.strip(),
            sex          = (bp.sex or None),
            birth_date   = _parse_date(bp.birth_date),
            death_date   = _parse_date(bp.death_date),
            birth_place  = (bp.birth_place or "").strip() or None,
            family_label = (bp.family_label or "").strip() or None,
        )
        db.add(person)
        await db.flush()                 # assigns person.id
        ref_to_id[bp.ref] = person.id

    seen: set[tuple[int, int, str]] = set()
    relations_created = 0
    for br in payload.relationships:
        if br.kind not in ALLOWED_KINDS:
            continue
        frm = ref_to_id.get(br.from_ref)
        to  = ref_to_id.get(br.to_ref)
        if not frm or not to or frm == to:
            continue
        key = (frm, to, br.kind)
        if key in seen:
            continue
        seen.add(key)
        db.add(Relationship(user_id=user.id, from_person_id=frm, to_person_id=to, kind=br.kind))
        relations_created += 1

    await db.commit()
    await _rebuild_graph_from_db(db, user.id)
    log.info("bulk_tree", persons=len(ref_to_id), relations=relations_created)
    return {"persons_created": len(ref_to_id), "relations_created": relations_created}


@router.post("/genealogy/relationships", status_code=201)
async def create_relationship(
    payload: RelationshipCreate,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Link two persons (``pai`` / ``mãe`` / ``cônjuge``) — owner only."""
    if payload.kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Permitidos: {sorted(ALLOWED_KINDS)}")
    if payload.from_person_id == payload.to_person_id:
        raise HTTPException(status_code=400, detail="Uma pessoa não pode relacionar-se consigo própria.")

    owned = (await db.execute(
        select(Person.id).where(
            Person.id.in_([payload.from_person_id, payload.to_person_id]),
            Person.user_id == user.id,
        )
    )).scalars().all()
    if set(owned) != {payload.from_person_id, payload.to_person_id}:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")

    existing = (await db.execute(
        select(Relationship).where(
            Relationship.user_id        == user.id,
            Relationship.from_person_id == payload.from_person_id,
            Relationship.to_person_id   == payload.to_person_id,
            Relationship.kind           == payload.kind,
        )
    )).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "from": existing.from_person_id, "to": existing.to_person_id, "kind": existing.kind}

    rel = Relationship(
        user_id        = user.id,
        from_person_id = payload.from_person_id,
        to_person_id   = payload.to_person_id,
        kind           = payload.kind,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    await _rebuild_graph_from_db(db, user.id)
    log.info("relationship_created", id=rel.id, kind=rel.kind)
    return {"id": rel.id, "from": rel.from_person_id, "to": rel.to_person_id, "kind": rel.kind}


@router.delete("/genealogy/relationships/{relationship_id}", status_code=204)
async def delete_relationship(
    relationship_id: int,
    db:              AsyncSession = Depends(get_db),
    user:            User         = Depends(get_current_user),
):
    """Remove a relationship — owner only."""
    rel = (await db.execute(
        select(Relationship).where(
            Relationship.id == relationship_id, Relationship.user_id == user.id
        )
    )).scalar_one_or_none()
    if not rel:
        raise HTTPException(status_code=404, detail="Relação não encontrada")
    await db.delete(rel)
    await db.commit()
    await _rebuild_graph_from_db(db, user.id)
    log.info("relationship_deleted", id=relationship_id)
