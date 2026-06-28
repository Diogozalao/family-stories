import asyncio

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.media import MediaFile, ProcessingStatus
from backend.models.narrative import Story, StoryStatus
from backend.models.timeline import Person, Relationship, TimelineEvent
from backend.modules.m2_temporal.family_graph import FamilyGraph
from backend.modules.m3_narrative.llm_client import LLMClient, LLMUnavailableError
from backend.modules.m3_narrative.rag_system import RAGSystem
from backend.modules.m3_narrative.pt_pt import count_brasileirismos, pt_pt_postprocess
from backend.modules.m3_narrative.templates import (
    GROUNDING_RULES,
    NARRATIVE_TEMPLATES,
    ORIGINALITY_RULES,
    get_template,
)

log = structlog.get_logger()


class NarrativeGenerator:
    def __init__(self):
        self.rag = RAGSystem()
        self.llm = LLMClient()
        log.info("m3_ready",
            rag_facts   = self.rag.total_facts,
            llm_backend = self.llm.backend,
        )

    async def _build_graph_from_db(self, db: AsyncSession, user_id, project_id=None) -> FamilyGraph:
        """Build the family graph straight from the DB (persons + relationships).

        The DB (Supabase) is the source of truth. The old on-disk JSON graph
        is unreliable in production: Render's free disk is **ephemeral** and is
        wiped on every restart/deploy, so the file is usually missing and the
        narrative loses ALL genealogical context — which is exactly why stories
        used to invent relatives and relationships. Building from the DB here
        guarantees the tree, the kinship links and each person's notes always
        reach the prompt. Scoped to ``project_id`` (a project story uses only
        that project's family) or the global family when None.
        """
        pstmt = select(Person).where(Person.user_id == user_id)
        pstmt = pstmt.where(Person.project_id == project_id) if project_id is not None \
            else pstmt.where(Person.project_id.is_(None))
        persons = (await db.execute(pstmt)).scalars().all()
        person_ids = {p.id for p in persons}
        rels = [r for r in (await db.execute(
            select(Relationship).where(Relationship.user_id == user_id)
        )).scalars().all() if r.from_person_id in person_ids and r.to_person_id in person_ids]

        graph = FamilyGraph()
        for p in persons:
            graph.add_person(p)
        for r in rels:
            graph.add_relation(r.from_person_id, r.to_person_id, r.kind)
            # Parent edges are directional; add the reverse so the context can
            # also phrase it from the child's side ("filho de …").
            if r.kind in ("pai", "mãe"):
                graph.add_relation(r.to_person_id, r.from_person_id, "filho de")
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
        media_ids:        list = None,
        project_id:       int  = None,
        custom_tone:      str  = None,
        custom_structure: str  = None,
        language:         str  = "pt",
        voice:            str  = None,
        subtitles:        bool = True,
        subtitle_size:    str  = "medium",
        update_story_id:  int  = None,
    ) -> Story:

        log.info("generating_narrative",
            title=title, type=event_type, project_id=project_id, user_id=str(user_id))

        # A project story uses ONLY that project's isolated family + photos;
        # a global story uses the global family + Library.
        graph    = await self._build_graph_from_db(db, user_id, project_id)
        template = get_template(event_type)

        media_stmt = select(MediaFile).where(
            MediaFile.user_id == user_id,
            MediaFile.status  == ProcessingStatus.COMPLETED,
        )
        if project_id is not None:
            from backend.models.project import Project
            # Confirm the project is actually owned by the caller.
            owns = (await db.execute(
                select(Project.id).where(Project.id == project_id, Project.user_id == user_id)
            )).scalar_one_or_none()
            if owns is None:
                raise PermissionError("Project not found for this user")
            media_stmt = media_stmt.where(MediaFile.project_id == project_id)
        else:
            media_stmt = media_stmt.where(MediaFile.project_id.is_(None))
        all_media = (await db.execute(media_stmt)).scalars().all()

        # Explicit photo selection overrides everything: when the user picked
        # specific photos/documents in the wizard, the narrative — and the
        # video built from it — use ONLY those, never the rest of the library.
        if media_ids:
            wanted = set(media_ids)
            chosen = [m for m in all_media if m.id in wanted]
            if chosen:
                all_media = chosen
                log.info("media_explicit_selection", selected=len(chosen))

        # ── RAG retrieval ────────────────────────────────────────────────
        # When the library is large and the user gave a focus, narrow the
        # photos down to the ones the RAG considers relevant to the theme
        # before building the prompt. This is the retrieval half of RAG —
        # it keeps the context focused and within the model's window. In
        # stub mode (no ChromaDB) ``search_media_ids`` returns [] and we
        # transparently keep every photo.
        focus_for_retrieval = (query or title or "").strip()
        if focus_for_retrieval and not media_ids and len(all_media) > 12:
            try:
                relevant_ids = set(self.rag.search_media_ids(
                    focus_for_retrieval, user_id, n_results=14))
                if relevant_ids:
                    selected = [m for m in all_media if m.id in relevant_ids]
                    if len(selected) >= 4:
                        log.info("rag_narrowed_media",
                                 total=len(all_media), kept=len(selected))
                        all_media = selected
            except Exception as exc:                       # never block generation
                log.warning("rag_select_failed", error=str(exc))

        # Map person id → name so each photo's context can name who appears
        # in it (the photo↔person tagging) — connecting faces to the tree.
        # Scoped to the same family as the graph (project or global).
        pn_stmt = select(Person.id, Person.name).where(Person.user_id == user_id)
        pn_stmt = pn_stmt.where(Person.project_id == project_id) if project_id is not None \
            else pn_stmt.where(Person.project_id.is_(None))
        person_rows  = (await db.execute(pn_stmt)).all()
        person_names = {pid: name for pid, name in person_rows}

        events_context = self._build_events_from_media(all_media, person_names)
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

        # Append the factual-grounding rules to every template at once — they
        # stop the model from inventing relatives/relationships and from
        # narrating to an undefined "tu" (the two biggest quality complaints).
        prompt += "\n\n" + GROUNDING_RULES
        # ...and the originality rules, which push the model off its default
        # clichés towards a fresh, concrete narrative for *this* family.
        prompt += "\n\n" + ORIGINALITY_RULES

        # The templates are written in Portuguese; we steer the LLM with a
        # short suffix that overrides the output language when the caller
        # asks for English. Llama 3.1 and Gemini both honour this without
        # needing parallel template translations.
        lang_code = (language or "pt").lower()
        if lang_code == "en":
            prompt += (
                "\n\nIMPORTANT: Write the entire narrative in natural, "
                "literary English (British). Do not include any Portuguese "
                "words except for proper nouns (people, places). Keep the "
                "memoir tone and the structure described above."
            )
        else:
            prompt += "\n\nIMPORTANTE: Escreve a narrativa inteira em português europeu (pt-PT)."

        try:
            # The LLM SDK call is synchronous and takes ~30 s. Off-load it to a
            # worker thread so the FastAPI event loop stays responsive (health
            # checks / keep-alive pings keep flowing) while we run synchronously.
            narrative_text = await asyncio.to_thread(
                self.llm.generate,
                prompt,
                settings.NARRATIVE_MAX_TOKENS,
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

        # ── pt-PT safety net ─────────────────────────────────────────────
        # Instruction alone doesn't keep Llama/Gemini from drifting into
        # Brazilian Portuguese, so mechanically correct the common tells
        # (vocabulary + "auxiliar + gerúndio") on the final text. No-op for
        # English narratives.
        if lang_code == "pt":
            before = count_brasileirismos(narrative_text)
            narrative_text, fixed = pt_pt_postprocess(narrative_text)
            if fixed:
                log.info("pt_pt_corrected",
                         title=title, tells_before=before, substitutions=fixed)

        # ── Scene segmentation ───────────────────────────────────────────
        # Pair each paragraph of prose with the photos that illustrate it,
        # so M4 can sync each photo to its stretch of narration. Defensive:
        # any failure here just leaves ``scenes=None`` and M4 falls back to
        # the legacy even-split slideshow.
        scenes = None
        try:
            from backend.modules.m3_narrative.scene_builder import build_scenes
            scenes = build_scenes(narrative_text, all_media) or None
            if scenes:
                log.info("scenes_built", n_scenes=len(scenes),
                         photos=sum(len(s["photo_ids"]) for s in scenes))
        except Exception as exc:
            log.warning("scene_build_failed", error=str(exc))

        media_id_list = [m.id for m in all_media]

        if update_story_id is not None:
            # Regenerate-with-feedback: rewrite the EXISTING story in place
            # (same id/title/settings), just a fresh narrative + scenes.
            story = (await db.execute(
                select(Story).where(Story.id == update_story_id, Story.user_id == user_id)
            )).scalar_one_or_none()
            if story is None:
                raise ValueError(f"Story {update_story_id} not found")
            story.narrative     = narrative_text
            story.template_used = template["name"]
            story.llm_backend   = self.llm.backend
            story.facts_used    = len(all_media)
            story.prompt_used   = prompt
            story.scenes        = scenes
            story.media_ids     = media_id_list
        else:
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
                language      = lang_code,
                voice         = voice,
                subtitles     = subtitles,
                subtitle_size = subtitle_size,
                scenes        = scenes,
                # The exact photos this narrative was built from — the video
                # (M4) reuses ONLY these (never the whole library).
                media_ids     = media_id_list,
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

    def _build_events_from_media(self, media_list: list, person_names: dict | None = None) -> str:
        if not media_list:
            return "Sem fotografias ou documentos disponíveis."

        lines = []
        for i, m in enumerate(media_list, 1):
            parts = []
            if m.ai_description:      parts.append(f"Descrição: {m.ai_description}")
            if person_names:
                who = [person_names.get(pid) for pid in (getattr(m, "person_ids", None) or [])]
                who = [n for n in who if n]
                if who:               parts.append(f"Quem aparece: {', '.join(who)}")
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
