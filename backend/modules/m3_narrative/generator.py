import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.media import MediaFile, ProcessingStatus
from backend.models.timeline import TimelineEvent
from backend.models.narrative import Story, StoryStatus
from backend.modules.m3_narrative.templates import get_template, NARRATIVE_TEMPLATES
from backend.modules.m3_narrative.rag_system import RAGSystem
from backend.modules.m3_narrative.llm_client import LLMClient
from backend.modules.m2_temporal.family_graph import FamilyGraph
from backend.core.config import settings

log = structlog.get_logger()


class NarrativeGenerator:
    def __init__(self):
        self.rag   = RAGSystem()
        self.llm   = LLMClient()
        self.graph = FamilyGraph()

        graph_path = settings.PROCESSED_DIR / "family_graph.json"
        self.graph.load(graph_path)

        log.info("m3_ready",
            rag_facts   = self.rag.total_facts,
            llm_backend = self.llm.backend,
            graph_nodes = len(self.graph.graph.nodes)
        )

    async def index_all(self, db: AsyncSession) -> dict:
        media_result = await db.execute(
            select(MediaFile).where(MediaFile.status == ProcessingStatus.COMPLETED)
        )
        media_list  = media_result.scalars().all()
        media_count = self.rag.index_media(media_list)

        events_result = await db.execute(select(TimelineEvent))
        events_list   = events_result.scalars().all()
        events_count  = self.rag.index_events(events_list)

        return {
            "media_indexed":  media_count,
            "events_indexed": events_count,
            "total_facts":    self.rag.total_facts,
        }

    async def generate(
        self,
        db:         AsyncSession,
        title:      str,
        event_type: str  = "default",
        query:      str  = None,
        person_ids: list = None,
    ) -> Story:

        log.info("generating_narrative", title=title, type=event_type)

        template = get_template(event_type)

        # Vai buscar os media reais directamente da BD
        media_result = await db.execute(
            select(MediaFile).where(MediaFile.status == ProcessingStatus.COMPLETED)
        )
        all_media = media_result.scalars().all()

        # Constrói contexto directamente dos media — evita alucinações
        events_context = self._build_events_from_media(all_media)
        family_context = self._build_family_context(person_ids)

        prompt = template["prompt"].format(
            tone           = template["tone"],
            structure      = template["structure"],
            family_context = family_context,
            events_context = events_context,
        )

        narrative_text = self.llm.generate(prompt, max_tokens=1000)

        story = Story(
            title         = title,
            event_type    = event_type,
            narrative     = narrative_text,
            template_used = template["name"],
            llm_backend   = self.llm.backend,
            facts_used    = len(all_media),
            prompt_used   = prompt,
            status        = StoryStatus.COMPLETED,
            person_ids    = person_ids or [],
        )
        db.add(story)
        await db.commit()
        await db.refresh(story)

        log.info("narrative_generated",
            id      = story.id,
            chars   = len(narrative_text),
            backend = self.llm.backend,
        )
        return story

    def _build_events_from_media(self, media_list: list) -> str:
        """
        Constrói contexto directamente dos media processados pelo M1.
        Isto previne alucinações — o LLM só tem acesso a factos reais.
        """
        if not media_list:
            return "Sem fotografias ou documentos disponíveis."

        lines = []
        for i, m in enumerate(media_list, 1):
            parts = []
            if m.ai_description:
                parts.append(f"Descrição: {m.ai_description}")
            if m.ai_setting:
                parts.append(f"Local: {m.ai_setting}")
            if m.ai_emotion:
                parts.append(f"Emoção: {m.ai_emotion}")
            if m.ai_tags:
                parts.append(f"Tags: {', '.join(m.ai_tags)}")
            if m.ai_narrative_hint:
                parts.append(f"Sugestão: {m.ai_narrative_hint}")
            if m.date_taken:
                parts.append(f"Data: {m.date_taken.strftime('%d/%m/%Y')}")
            if m.ocr_text:
                parts.append(f"Texto: {m.ocr_text[:200]}")

            if parts:
                lines.append(f"[Momento {i}]\n" + "\n".join(parts))

        return "\n\n".join(lines)

    def _build_family_context(self, person_ids: list = None) -> str:
        summary = self.graph.get_narrative_summary()
        if summary and summary != "Família sem dados genealógicos definidos.":
            return f"Relações familiares: {summary}"
        return "Sem dados genealógicos. Baseia-te apenas nos momentos descritos."
