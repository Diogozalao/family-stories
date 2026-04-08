import uuid
import shutil
import mimetypes
import structlog
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.core.config import settings
from backend.modules.m1_ingestion.exif_extractor import ExifExtractor
from backend.modules.m1_ingestion.gemini_analyzer import GeminiAnalyzer
from backend.modules.m1_ingestion.ocr_extractor import OCRExtractor
from backend.modules.m1_ingestion.security_scanner import SecurityScanner

log = structlog.get_logger()

# Mapeamento MIME → tipo de média
MIME_TO_TYPE = {
    "image/jpeg":      MediaType.PHOTO,
    "image/png":       MediaType.PHOTO,
    "image/tiff":      MediaType.PHOTO,
    "image/heic":      MediaType.PHOTO,
    "image/heif":      MediaType.PHOTO,
    "video/mp4":       MediaType.VIDEO,
    "video/quicktime": MediaType.VIDEO,
    "video/avi":       MediaType.VIDEO,
    "application/pdf": MediaType.DOCUMENT,
    "text/plain":      MediaType.DOCUMENT,
}

class M1Processor:
    """
    Orquestra todo o pipeline de ingestão multimodal:
    1. Segurança (ClamAV + checksum)
    2. Armazenamento seguro
    3. Extração EXIF (fotos)
    4. Análise Gemini Vision (fotos)
    5. OCR (documentos)
    6. Guarda resultados na BD
    """

    def __init__(self):
        self.exif      = ExifExtractor()
        self.gemini    = GeminiAnalyzer()
        self.ocr       = OCRExtractor()
        self.security  = SecurityScanner()

        # Garantir pastas
        settings.RAW_DIR.mkdir(parents=True, exist_ok=True)
        for sub in ["photos", "videos", "documents", "gedcom"]:
            (settings.RAW_DIR / sub).mkdir(exist_ok=True)

    async def process(self, file_path: Path, original_filename: str, db: AsyncSession, ai_override: dict = None) -> MediaFile:
        log.info("m1_start", file=original_filename)

        # Detecta tipo MIME
        mime, _ = mimetypes.guess_type(original_filename)
        media_type = MIME_TO_TYPE.get(mime, MediaType.DOCUMENT)

        # Cria registo inicial na BD
        record = MediaFile(
            original_filename=original_filename,
            stored_filename=file_path.name,
            file_path=str(file_path),
            file_size=file_path.stat().st_size,
            mime_type=mime,
            media_type=media_type,
            status=ProcessingStatus.PROCESSING,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        try:
            # 1. Segurança
            log.info("m1_security_scan", file=original_filename)
            sec = self.security.scan(file_path)
            record.checksum_md5 = sec["checksum_md5"]
            record.is_safe = sec["is_safe"]

            if not sec["is_safe"]:
                record.status = ProcessingStatus.FAILED
                record.error_message = sec.get("error", "Ficheiro não seguro")
                await db.commit()
                return record

            # 2. EXIF (apenas fotos/vídeos)
            if media_type in (MediaType.PHOTO, MediaType.VIDEO):
                log.info("m1_exif", file=original_filename)
                exif_data = self.exif.extract(file_path)
                record.date_taken   = exif_data.get("date_taken")
                record.latitude     = exif_data.get("latitude")
                record.longitude    = exif_data.get("longitude")
                record.camera_make  = exif_data.get("camera_make")
                record.camera_model = exif_data.get("camera_model")
                record.raw_exif     = exif_data.get("raw_exif")

            # 3. Gemini Vision (apenas fotos)
            if media_type == MediaType.PHOTO:
                log.info("m1_gemini", file=original_filename)
                ai_data = ai_override if ai_override else self.gemini.analyze(file_path)
                record.ai_description    = ai_data.get("ai_description")
                record.ai_people_count   = ai_data.get("ai_people_count")
                record.ai_setting        = ai_data.get("ai_setting")
                record.ai_emotion        = ai_data.get("ai_emotion")
                record.ai_tags           = ai_data.get("ai_tags")
                record.ai_narrative_hint = ai_data.get("ai_narrative_hint")

            # 4. OCR (documentos e fotos com texto)
            if media_type == MediaType.DOCUMENT:
                log.info("m1_ocr", file=original_filename)
                record.ocr_text = self.ocr.extract(file_path)

            record.status = ProcessingStatus.COMPLETED
            log.info("m1_complete", file=original_filename, id=record.id)

        except Exception as e:
            log.error("m1_failed", file=original_filename, error=str(e))
            record.status = ProcessingStatus.FAILED
            record.error_message = str(e)

        await db.commit()
        await db.refresh(record)
        return record


async def process_gedcom(file_path: Path, db) -> dict:
    """Processa ficheiro GEDCOM e importa árvore genealógica."""
    from backend.modules.m1_ingestion.gedcom_parser import gedcom_to_database
    return await gedcom_to_database(file_path, db)
