import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.models.narrative import Story
from backend.schemas.narrative import GenerateRequest, StoryResponse
from backend.modules.m3_narrative.generator import NarrativeGenerator
from backend.modules.m3_narrative.templates import NARRATIVE_TEMPLATES

router = APIRouter(prefix="/api/v1", tags=["narrativa"])
log    = structlog.get_logger()

generator = NarrativeGenerator()


@router.post("/narrative/index")
async def index_facts(db: AsyncSession = Depends(get_db)):
    """
    Indexa todos os factos do M1/M2 no sistema RAG.
    Chama este endpoint antes de gerar narrativas.
    """
    result = await generator.index_all(db)
    return {
        "message": "Factos indexados com sucesso",
        **result
    }


@router.post("/narrative/generate", response_model=StoryResponse)
async def generate_narrative(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Gera uma narrativa familiar com LLM + RAG.
    
    event_type disponíveis: default, fotografia, casamento,
    viagem, nascimento, celebração
    """
    if request.event_type not in NARRATIVE_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"event_type inválido. Disponíveis: {list(NARRATIVE_TEMPLATES.keys())}"
        )

    story = await generator.generate(
        db          = db,
        title       = request.title,
        event_type  = request.event_type,
        query       = request.query,
        person_ids  = request.person_ids,
    )
    return story


@router.get("/narrative/templates")
async def list_templates():
    """Lista todos os templates narrativos disponíveis."""
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
    """Lista todas as histórias geradas."""
    result = await db.execute(
        select(Story).order_by(Story.created_at.desc())
    )
    return result.scalars().all()


@router.get("/narrative/stories/{story_id}", response_model=StoryResponse)
async def get_story(story_id: int, db: AsyncSession = Depends(get_db)):
    """Retorna uma história específica."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="História não encontrada")
    return story


@router.delete("/narrative/stories/{story_id}")
async def delete_story(story_id: int, db: AsyncSession = Depends(get_db)):
    """Apaga uma história."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Não encontrada")
    await db.delete(story)
    await db.commit()
    return {"message": "Apagada com sucesso"}


@router.get("/narrative/rag/stats")
async def rag_stats():
    """Estatísticas do sistema RAG — útil para o relatório."""
    return {
        "total_facts_indexed": generator.rag.total_facts,
        "llm_backend":         generator.llm.backend,
        "graph_persons":       len(generator.graph.graph.nodes),
        "graph_relations":     len(generator.graph.graph.edges),
    }
