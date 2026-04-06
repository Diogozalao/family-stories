import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.timeline import TimelineEvent, ConfidenceLevel
from backend.modules.m2_temporal.timeline_builder import TimelineBuilder
from backend.modules.m2_temporal.family_graph import FamilyGraph
from backend.modules.m2_temporal.date_resolver import DateResolver
from backend.core.config import settings

log = structlog.get_logger()

class M2Processor:
    """
    Orquestra o Módulo 2 — Organização Temporal:
    1. Constrói timeline a partir dos media do M1
    2. Valida e corrige datas
    3. Constrói/atualiza grafo de relações familiares
    4. Devolve timeline ordenada pronta para o M3
    """

    def __init__(self):
        self.builder  = TimelineBuilder()
        self.graph    = FamilyGraph()
        self.resolver = DateResolver()
        
        # Carrega grafo existente se houver
        graph_path = settings.PROCESSED_DIR / "family_graph.json"
        self.graph.load(graph_path)

    async def process(self, db: AsyncSession) -> dict:
        log.info("m2_start")

        # 1. Constrói eventos a partir de media não processados
        new_events = await self.builder.build_from_media(db)

        # 2. Valida datas de todos os eventos
        all_events_result = await db.execute(select(TimelineEvent))
        all_events = all_events_result.scalars().all()

        fixed = 0
        for event in all_events:
            corrected, note = self.resolver.validate_and_fix(
                event.event_date, source=f"event_{event.id}"
            )
            if corrected != event.event_date:
                event.event_date      = corrected
                event.date_confidence = ConfidenceLevel.LOW
                event.date_label      = note
                fixed += 1

        await db.commit()

        # 3. Ordena a timeline
        sorted_events = self.resolver.sort_events(all_events)

        # 4. Guarda grafo atualizado
        graph_path = settings.PROCESSED_DIR / "family_graph.json"
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.graph.save(graph_path)

        result = {
            "total_events":     len(all_events),
            "new_events":       len(new_events),
            "dates_fixed":      fixed,
            "graph_stats":      self.graph.stats,
            "timeline_preview": [
                {
                    "id":         e.id,
                    "date":       str(e.event_date) if e.event_date else None,
                    "confidence": e.date_confidence,
                    "label":      e.date_label,
                    "type":       e.event_type,
                    "title":      e.title,
                }
                for e in sorted_events[:10]  # Primeiros 10 para preview
            ]
        }

        log.info("m2_complete", **{k: v for k, v in result.items() if k != "timeline_preview"})
        return result
