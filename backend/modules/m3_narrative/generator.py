import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.media import MediaFile, ProcessingStatus
from backend.models.narrative import Story, StoryStatus
from backend.models.timeline import TimelineEvent
from backend.modules.m2_temporal.family_graph import FamilyGraph
from backend.modules.m3_narrative.llm_client import LLMClient, LLMUnavailableError
from backend.modules.m3_narrative.rag_system import RAGSystem
from backend.modules.m3_narrative.templates import NARRATIVE_TEMPLATES, get_template

log = structlog.get_logger()


def _graph_path_for(user_id) -> "object":
    """Return the on-disk path of the family graph belonging to ``user_id``.

    Each user has their own graph file — sharing a single
    ``family_graph.json`` across the archive would leak relatives between
    accounts, defeating the whole point of the multi-tenant migration.
    """
    folder = settings.PROCESSED_DIR / "graphs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{user_id}.json"


class NarrativeGenerator:
    def __init__(self):
        self.rag = RAGSystem()
        self.llm = LLMClient()
        log.info("m3_ready",
            rag_facts   = self.rag.total_facts,
            llm_backend = self.llm.backend,
        )

    def _load_graph(self, user_id) -> FamilyGraph:
        """Build a fresh ``FamilyGraph`` for the caller — always per-user.

        We do NOT keep a process-level graph cached across requests:
        sharing it would cross user boundaries, and reloading is cheap
        compared to the LLM call that follows.
        """
        graph = FamilyGraph()
        graph.load(_graph_path_for(user_id))
        return graph

    async def index_all(self, db: AsyncSession, user_id) -> dict:
        """Reindexa o RAG só com os factos do utilizador autenticado."""
        media_result = await db.execute(
            select(MediaFile).where(
                MediaFile.user_id == user_id,
                MediaFile.status  == ProcessingStatus.COMPLETED,
            )
        )
        media_list  = media_result.scalars().all()
        media_count = self.rag.index_media(media_list)

        events_result = await db.execute(
            select(TimelineEvent).where(TimelineEvent.user_id == user_id)
        )
        events_list  = events_result.scalars().all()
        events_count = self.rag.index_events(events_list)

        return {
            "media_indexed":  media_count,
            "events_indexed": events_count,
            "total_facts":    self.rag.count_for(user_id),
        }

    async def generate(
        self,
        db:               AsyncSession,
        user_id,
        title:            str,
        event_type:       str  = "default",
        query:            str  = None,
        person_ids:       list = None,
        project_id:       int  = None,
        custom_tone:      str  = None,
        custom_structure: str  = None,
    ) -> Story:

        log.info("generating_narrative",
            title=title, type=event_type, project_id=project_id, user_id=str(user_id))

        graph    = self._load_graph(user_id)
        template = get_template(event_type)

        # When scoped to a project, only consider media that's (a) owned by
        # the caller AND (b) attached to that project. Outside of a project,
        # consider every completed media owned by the caller.
        if project_id is not None:
            from backend.models.project import Project, ProjectMedia
            # First confirm the project is actually owned by the caller —
            # otherwise we'd happily generate narratives over a stranger's
            # project just because its id was passed in.
            owns = (await db.execute(
                select(Project.id).where(Project.id == project_id, Project.user_id == user_id)
            )).scalar_one_or_none()
            if owns is None:
                raise PermissionError("Project not found for this user")

            media_result = await db.execute(
                select(MediaFile)
                .join(ProjectMedia, ProjectMedia.media_id == MediaFile.id)
                .where(
                    ProjectMedia.project_id == project_id,
                    MediaFile.user_id       == user_id,
                    MediaFile.status        == ProcessingStatus.COMPLETED,
                )
            )
        else:
            media_result = await db.execute(
                select(MediaFile).where(
                    MediaFile.user_id == user_id,
                    MediaFile.status  == ProcessingStatus.COMPLETED,
                )
            )
        all_media = media_result.scalars().all()

        events_context = self._build_events_from_media(all_media)
        family_context = self._build_family_context(graph, person_ids)

        user_focus = (query or title or "").strip()
        if not user_focus:
            user_focus = "(o utilizador não indicou um tema específico — usa os factos disponíveis com naturalidade.)"

        tone      = (custom_tone      or template["tone"])      if event_type == "custom" else template["tone"]
        structure = (custom_structure or template["structure"]) if event_type == "custom" else template["structure"]

        prompt = template["prompt"].format(
            tone           = tone,
            structure      = structure,
            family_context = family_context,
            events_context = events_context,
            user_focus     = user_focus,
        )

        try:
            narrative_text = self.llm.generate(
                prompt,
                max_tokens=settings.NARRATIVE_MAX_TOKENS,
            )
        except LLMUnavailableError as exc:
            log.error("narrative_llm_unavailable", title=title, error=str(exc))
            raise

        if not narrative_text or len(narrative_text.strip()) < 30:
            log.error("narrative_too_short", title=title, chars=len(narrative_text or ""))
            raise LLMUnavailableError(
                "The LLM returned an empty or trivially short response — "
                "treating as a generation failure."
            )

        story = Story(
            user_id       = user_id,
            title         = title,
            event_type    = event_type,
            narrative     = narrative_text,
            template_used = template["name"],
            llm_backend   = self.llm.backend,
            facts_used    = len(all_media),
            prompt_used   = prompt,
            status        = StoryStatus.COMPLETED,
            person_ids    = person_ids or [],
            project_id    = project_id,
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
        if not media_list:
            return "Sem fotografias ou documentos disponíveis."

        lines = []
        for i, m in enumerate(media_list, 1):
            parts = []
            if m.ai_description:      parts.append(f"Descrição: {m.ai_description}")
            if m.ai_setting:          parts.append(f"Local: {m.ai_setting}")
            if m.ai_emotion:          parts.append(f"Emoção: {m.ai_emotion}")
            if m.ai_tags:             parts.append(f"Tags: {', '.join(m.ai_tags)}")
            if m.ai_narrative_hint:   parts.append(f"Sugestão: {m.ai_narrative_hint}")
            if m.date_taken:          parts.append(f"Data: {m.date_taken.strftime('%d/%m/%Y')}")
            if m.ocr_text:            parts.append(f"Texto: {m.ocr_text[:200]}")
            if parts:
                lines.append(f"[Momento {i}]\n" + "\n".join(parts))

        return "\n\n".join(lines)

    def _build_family_context(self, graph: FamilyGraph, person_ids: list = None) -> str:
        if person_ids:
            context = graph.get_persons_context(person_ids)
        else:
            context = graph.get_narrative_summary()

        if context and context not in ("Família sem dados genealógicos definidos.", ""):
            return f"Relações familiares conhecidas: {context}"
        return "Sem dados genealógicos disponíveis. Baseia-te apenas nos momentos descritos."
