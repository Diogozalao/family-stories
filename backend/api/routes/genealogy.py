import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import uuid, aiofiles

from backend.core.database import get_db
from backend.core.config import settings
from backend.models.timeline import Person
from backend.modules.m1_ingestion.gedcom_parser import gedcom_to_database

router = APIRouter(prefix="/api/v1", tags=["genealogia"])
log    = structlog.get_logger()


@router.post("/genealogy/upload")
async def upload_gedcom(
    file: UploadFile = File(...),
    db:   AsyncSession = Depends(get_db)
):
    """
    Faz upload de ficheiro GEDCOM (.ged) e importa a árvore genealógica.
    Exporta de: Ancestry, MyHeritage, FamilySearch, Geneanet, etc.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in {".ged", ".gedcom"}:
        raise HTTPException(
            status_code=400,
            detail="Ficheiro deve ser .ged ou .gedcom (exportado de Ancestry/MyHeritage/etc.)"
        )

    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path   = settings.RAW_DIR / "gedcom" / unique_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(await file.read())

    log.info("gedcom_uploaded", filename=file.filename)

    # Processa e importa
    result = await gedcom_to_database(dest_path, db)

    return {
        "message":  "Árvore genealógica importada com sucesso",
        "filename": file.filename,
        **result
    }


@router.get("/genealogy/persons")
async def list_persons(db: AsyncSession = Depends(get_db)):
    """Lista todas as pessoas importadas do GEDCOM."""
    result = await db.execute(select(Person).order_by(Person.name))
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
async def get_person(person_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna detalhes de uma pessoa e as suas relações familiares."""
    person = await db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada")

    from backend.modules.m2_temporal.family_graph import FamilyGraph
    graph      = FamilyGraph()
    graph_path = settings.PROCESSED_DIR / "family_graph.json"
    graph.load(graph_path)
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
async def get_graph():
    """Retorna o grafo familiar completo — útil para visualização."""
    from backend.modules.m2_temporal.family_graph import FamilyGraph
    graph      = FamilyGraph()
    graph_path = settings.PROCESSED_DIR / "family_graph.json"
    graph.load(graph_path)

    return {
        "nodes":   [{"id": n, **graph.graph.nodes[n]} for n in graph.graph.nodes],
        "edges":   [{"from": u, "to": v, **d} for u, v, d in graph.graph.edges(data=True)],
        "summary": graph.get_narrative_summary(),
        "stats":   graph.stats,
    }


@router.delete("/genealogy/persons")
async def clear_persons(db: AsyncSession = Depends(get_db)):
    """Limpa todas as pessoas — para reimportar um GEDCOM."""
    from sqlalchemy import delete
    from backend.core.config import settings
    await db.execute(delete(Person))
    await db.commit()

    # Reset grafo
    graph_path = settings.PROCESSED_DIR / "family_graph.json"
    if graph_path.exists():
        graph_path.unlink()

    return {"message": "Todas as pessoas removidas"}
