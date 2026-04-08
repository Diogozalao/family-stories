import structlog
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.models.timeline import TimelineEvent, ConfidenceLevel

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

    async def build_from_media(self, db: AsyncSession) -> list[TimelineEvent]:
        # Busca todos os media processados sem evento ainda
        result = await db.execute(
            select(MediaFile).where(
                MediaFile.status == ProcessingStatus.COMPLETED,
                MediaFile.media_type.in_([MediaType.PHOTO, MediaType.VIDEO, MediaType.DOCUMENT])
            )
        )
        media_files = result.scalars().all()
        log.info("timeline_build_start", total_files=len(media_files))

        events = []
        for mf in media_files:
            # Verifica se já existe evento para este media
            existing = await db.execute(
                select(TimelineEvent).where(TimelineEvent.media_file_id == mf.id)
            )
            if existing.scalar_one_or_none():
                continue  # já processado

            event = self._create_event(mf)
            db.add(event)
            events.append(event)

        await db.commit()
        log.info("timeline_build_done", events_created=len(events))
        return events

    def _create_event(self, mf: MediaFile) -> TimelineEvent:
        date, confidence = self._resolve_date(mf)
        event_type = self._classify_event(mf)
        title = self._generate_title(mf, date)

        return TimelineEvent(
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


MESES_PT = {
    "January": "janeiro", "February": "fevereiro", "March": "março",
    "April": "abril", "May": "maio", "June": "junho",
    "July": "julho", "August": "agosto", "September": "setembro",
    "October": "outubro", "November": "novembro", "December": "dezembro"
}

def traduz_data(data_str: str) -> str:
    for en, pt in MESES_PT.items():
        data_str = data_str.replace(en, pt)
    return data_str
