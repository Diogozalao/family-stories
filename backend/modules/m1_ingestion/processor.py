"""Module 1 — Multimodal ingestion pipeline.

Receives raw file bytes, runs the AI/OCR/EXIF stack on a transient
temporary file, then uploads the same bytes to Supabase Storage under
``{user_id}/photos/{stored_filename}``. The local temp file is always
removed before returning.

``MediaFile.file_path`` is the Storage object key, not a disk path —
any code that previously read straight from disk has to fetch via
``backend.core.supabase_storage`` instead.
"""

import mimetypes
import tempfile
import uuid
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.supabase_storage import object_key_for, upload_bytes
from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.modules.m1_ingestion.exif_extractor import ExifExtractor
from backend.modules.m1_ingestion.gemini_analyzer import GeminiAnalyzer
from backend.modules.m1_ingestion.ocr_extractor import OCRExtractor
from backend.modules.m1_ingestion.security_scanner import SecurityScanner

log = structlog.get_logger()

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
    """Pipeline orchestrator: scan → EXIF → Gemini → OCR → Storage upload."""

    def __init__(self):
        self.exif     = ExifExtractor()
        self.gemini   = GeminiAnalyzer()
        self.ocr      = OCRExtractor()
        self.security = SecurityScanner()

    async def process(
        self,
        content:           bytes,
        original_filename: str,
        db:                AsyncSession,
        user_id,
        ai_override:       dict | None = None,
    ) -> MediaFile:
        """Ingest ``content`` for ``user_id`` and persist a ``MediaFile`` row.

        Returns the committed (and refreshed) ORM record.
        """
        log.info("m1_start", file=original_filename, user_id=str(user_id), bytes=len(content))

        mime, _    = mimetypes.guess_type(original_filename)
        media_type = MIME_TO_TYPE.get(mime, MediaType.DOCUMENT)

        # Stable, collision-free filename for both the temp file and the
        # Storage object — we don't want the original filename in the
        # path because two users could upload the same name.
        ext             = Path(original_filename).suffix.lower() or ""
        stored_filename = f"{uuid.uuid4().hex}{ext}"
        object_key      = object_key_for(user_id, "photos", stored_filename)

        # Work on a temp file because the AI/EXIF/OCR libraries all expect
        # a filesystem path. Cleaned up unconditionally in the finally.
        tmp_dir  = Path(tempfile.mkdtemp(prefix="m1_"))
        tmp_path = tmp_dir / stored_filename
        tmp_path.write_bytes(content)

        record = MediaFile(
            user_id           = user_id,
            original_filename = original_filename,
            stored_filename   = stored_filename,
            file_path         = object_key,     # Supabase Storage key, not a disk path.
            file_size         = len(content),
            mime_type         = mime,
            media_type        = media_type,
            status            = ProcessingStatus.PROCESSING,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        try:
            log.info("m1_security_scan", file=original_filename)
            sec = self.security.scan(tmp_path)
            record.checksum_md5 = sec["checksum_md5"]
            record.is_safe      = sec["is_safe"]

            if not sec["is_safe"]:
                record.status        = ProcessingStatus.FAILED
                record.error_message = sec.get("error", "Ficheiro não seguro")
                await db.commit()
                return record

            if media_type in (MediaType.PHOTO, MediaType.VIDEO):
                log.info("m1_exif", file=original_filename)
                exif_data = self.exif.extract(tmp_path)
                record.date_taken   = exif_data.get("date_taken")
                record.latitude     = exif_data.get("latitude")
                record.longitude    = exif_data.get("longitude")
                record.camera_make  = exif_data.get("camera_make")
                record.camera_model = exif_data.get("camera_model")
                record.raw_exif     = exif_data.get("raw_exif")

            if media_type == MediaType.PHOTO:
                log.info("m1_gemini", file=original_filename)
                ai_data = ai_override if ai_override else self.gemini.analyze(tmp_path)
                record.ai_description    = ai_data.get("ai_description")
                record.ai_people_count   = ai_data.get("ai_people_count")
                record.ai_setting        = ai_data.get("ai_setting")
                record.ai_emotion        = ai_data.get("ai_emotion")
                record.ai_tags           = ai_data.get("ai_tags")
                record.ai_narrative_hint = ai_data.get("ai_narrative_hint")

            if media_type == MediaType.DOCUMENT:
                log.info("m1_ocr", file=original_filename)
                record.ocr_text = self.ocr.extract(tmp_path)

            # Only push to Storage after a clean security scan — we never
            # want to host bytes the scanner flagged unsafe.
            log.info("m1_storage_upload", key=object_key)
            await upload_bytes(object_key, content, content_type=mime)

            record.status = ProcessingStatus.COMPLETED
            log.info("m1_complete", file=original_filename, id=record.id, key=object_key)

        except Exception as exc:
            log.error("m1_failed", file=original_filename, error=str(exc))
            record.status        = ProcessingStatus.FAILED
            record.error_message = str(exc)

        finally:
            # Always clean the temp scratch space.
            try:
                tmp_path.unlink(missing_ok=True)
                tmp_dir.rmdir()
            except OSError as exc:
                log.warning("m1_tmp_cleanup_failed", path=str(tmp_dir), error=str(exc))

        await db.commit()
        await db.refresh(record)
        return record


async def process_gedcom(file_path: Path, db: AsyncSession, user_id) -> dict:
    """Processa ficheiro GEDCOM e importa árvore genealógica para ``user_id``."""
    from backend.modules.m1_ingestion.gedcom_parser import gedcom_to_database
    return await gedcom_to_database(file_path, db, user_id=user_id)
