"""Module 2 — Organização Temporal.

Builds the per-user chronological timeline + family graph that the M3
narrative module consumes downstream. Every operation here is scoped
to a single ``user_id`` — the timeline and graph of one account never
mix with another's.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.timeline import ConfidenceLevel, TimelineEvent
from backend.modules.m2_temporal.date_resolver import DateResolver
from backend.modules.m2_temporal.family_graph import FamilyGraph
from backend.modules.m2_temporal.timeline_builder import TimelineBuilder

log = structlog.get_logger()


def _graph_path_for(user_id) -> "object":
    """Return the on-disk path of the family graph belonging to ``user_id``."""
    folder = settings.PROCESSED_DIR / "graphs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{user_id}.json"


class M2Processor:
    """Orquestra M2: timeline + grafo, sempre por utilizador."""

    def __init__(self):
        self.builder  = TimelineBuilder()
        self.resolver = DateResolver()

    def _load_graph(self, user_id) -> FamilyGraph:
        graph = FamilyGraph()
        graph.load(_graph_path_for(user_id))
        return graph

    async def process(self, db: AsyncSession, user_id) -> dict:
        log.info("m2_start", user_id=str(user_id))

        # 1. Build new timeline events from this user's M1 media.
        new_events = await self.builder.build_from_media(db, user_id=user_id)

        # 2. Validate and correct dates on this user's existing events.
        all_events_result = await db.execute(
            select(TimelineEvent).where(TimelineEvent.user_id == user_id)
        )
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

        # 3. Sort the events for preview.
        sorted_events = self.resolver.sort_events(all_events)

        # 4. Persist the (per-user) family graph snapshot to disk.
        graph = self._load_graph(user_id)
        graph.save(_graph_path_for(user_id))

        result = {
            "total_events":   len(all_events),
            "new_events":     len(new_events),
            "dates_fixed":    fixed,
            "graph_stats":    graph.stats,
            "timeline_preview": [
                {
                    "id":         e.id,
                    "date":       str(e.event_date) if e.event_date else None,
                    "confidence": e.date_confidence,
                    "label":      e.date_label,
                    "type":       e.event_type,
                    "title":      e.title,
                }
                for e in sorted_events[:10]
            ],
        }

        log.info("m2_complete", **{k: v for k, v in result.items() if k != "timeline_preview"})
        return result
