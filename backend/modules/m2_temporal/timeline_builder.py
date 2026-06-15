import structlog
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.models.timeline import TimelineEvent, ConfidenceLevel
from backend.utils.date_utils import data_para_portugues

log = structlog.get_logger()

# Mapeamento de emoção/setting para tipo de evento
EVENT_TYPE_MAP = {
    "casamento":    "casamento",
    "wedding":      "casamento",
    "aniversário":  "celebração",
    "birthday":     "celebração",
    "celebração":   "celebração",
    "praia":        "férias",
    "viagem":       "viagem",
    "viagem":       "viagem",
    "nascimento":   "nascimento",
    "bebé":         "nascimento",
    "graduação":    "graduação",
    "formatura":    "graduação",
    "natal":        "natal",
    "páscoa":       "páscoa",
}

class TimelineBuilder:
    """
    Constrói a timeline cronológica a partir dos ficheiros processados pelo M1.
    
    Para cada MediaFile com status=COMPLETED:
    - Cria um TimelineEvent com a data mais fiável disponível
    - Classifica o tipo de evento com base nos dados do Gemini
    - Atribui nível de confiança à data
    """

    async def build_from_media(self, db: AsyncSession, user_id) -> list[TimelineEvent]:
        """Build timeline events from media owned by ``user_id``.

        Restricted to that user's media so we never cross-pollinate the
        timeline with someone else's photos.
        """
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.user_id    == user_id,
                MediaFile.status     == ProcessingStatus.COMPLETED,
                MediaFile.media_type.in_([MediaType.PHOTO, MediaType.VIDEO, MediaType.DOCUMENT]),
            )
        )
        media_files = result.scalars().all()
        log.info("timeline_build_start", total_files=len(media_files), user_id=str(user_id))

        events = []
        for mf in media_files:
            existing = (await db.execute(
                select(TimelineEvent).where(
                    TimelineEvent.media_file_id == mf.id,
                    TimelineEvent.user_id       == user_id,
                )
            )).scalar_one_or_none()

            if existing:
                # Re-sync date/title/etc. from the media. This is what makes
                # the build idempotent and lets a later date fallback (or a
                # date the user edited) propagate to events created earlier.
                self._refresh_event(existing, mf)
                continue

            event = self._create_event(mf, user_id)
            db.add(event)
            events.append(event)

        await db.commit()
        log.info("timeline_build_done", events_created=len(events), total=len(media_files))
        return events

    def _refresh_event(self, event: TimelineEvent, mf: MediaFile) -> None:
        """Update a previously-built event with the media's current data."""
        date, confidence = self._resolve_date(mf)
        event.event_date      = date
        event.date_confidence = confidence
        event.date_label      = self._date_label(date, confidence)
        event.event_type      = self._classify_event(mf)
        event.title           = self._generate_title(mf, date)
        event.description     = mf.ai_description
        event.location        = mf.location_name or mf.ai_setting
        event.sort_order      = int(date.timestamp()) if date else 0

    def _create_event(self, mf: MediaFile, user_id) -> TimelineEvent:
        date, confidence = self._resolve_date(mf)
        event_type = self._classify_event(mf)
        title = self._generate_title(mf, date)

        return TimelineEvent(
            user_id         = user_id,
            event_date      = date,
            date_confidence = confidence,
            date_label      = self._date_label(date, confidence),
            event_type      = event_type,
            title           = title,
            description     = mf.ai_description,
            location        = mf.location_name or mf.ai_setting,
            latitude        = mf.latitude,
            longitude       = mf.longitude,
            media_file_id   = mf.id,
            person_ids      = [],
            sort_order      = int(date.timestamp()) if date else 0,
        )

    def _resolve_date(self, mf: MediaFile) -> tuple[Optional[datetime], ConfidenceLevel]:
        """
        Hierarquia de confiança:
        1. EXIF DateTimeOriginal → HIGH
        2. Data do ficheiro      → MEDIUM  
        3. Sem data              → LOW
        """
        if mf.date_taken:
            return mf.date_taken, ConfidenceLevel.HIGH
        if mf.created_at:
            return mf.created_at, ConfidenceLevel.MEDIUM
        return None, ConfidenceLevel.LOW

    def _classify_event(self, mf: MediaFile) -> str:
        """Classifica o tipo de evento com base nos dados do Gemini."""
        sources = [
            mf.ai_setting or "",
            mf.ai_emotion or "",
            " ".join(mf.ai_tags or []),
            mf.ai_description or "",
        ]
        text = " ".join(sources).lower()

        for keyword, event_type in EVENT_TYPE_MAP.items():
            if keyword in text:
                return event_type

        # Fallback por tipo de média
        if mf.media_type == MediaType.PHOTO:
            return "fotografia"
        elif mf.media_type == MediaType.VIDEO:
            return "vídeo"
        return "documento"

    def _generate_title(self, mf: MediaFile, date: Optional[datetime]) -> str:
        date_str = date.strftime("%d/%m/%Y") if date else "Data desconhecida"
        if mf.ai_setting:
            return f"{mf.ai_setting} — {date_str}"
        return f"{mf.original_filename} — {date_str}"

    def _date_label(self, date: Optional[datetime], confidence: ConfidenceLevel) -> str:
        if not date:
            return "Data desconhecida"
        if confidence == ConfidenceLevel.HIGH:
            return data_para_portugues(date.strftime("%d de %B de %Y"))
        if confidence == ConfidenceLevel.MEDIUM:
            return f"~{date.strftime('%Y')}"
        decade = (date.year // 10) * 10
        return f"Anos {decade}"


