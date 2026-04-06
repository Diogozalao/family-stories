import uuid
import aiofiles
import structlog
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from backend.core.config import settings
from backend.core.database import get_db, AsyncSessionLocal
from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.schemas.media import UploadResponse, MediaFileResponse
from backend.modules.m1_ingestion.processor import M1Processor

router = APIRouter(prefix="/api/v1", tags=["upload"])
log = structlog.get_logger()

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff",
    ".mp4", ".mov", ".avi",
    ".pdf", ".txt",
    ".ged", ".gedcom"
}

processor = M1Processor()


async def process_in_background(file_path: Path, original_filename: str, record_id: int):
    """
    Corre o processamento pesado (Gemini, OCR, EXIF) em background.
    O utilizador já recebeu resposta — isto corre silenciosamente.
    """
    async with AsyncSessionLocal() as db:
        try:
            record = await db.get(MediaFile, record_id)
            if not record:
                return

            # EXIF
            from backend.modules.m1_ingestion.exif_extractor import ExifExtractor
            exif_data = ExifExtractor().extract(file_path)
            record.date_taken   = exif_data.get("date_taken")
            record.latitude     = exif_data.get("latitude")
            record.longitude    = exif_data.get("longitude")
            record.camera_make  = exif_data.get("camera_make")
            record.camera_model = exif_data.get("camera_model")
            record.raw_exif     = exif_data.get("raw_exif")

            # Gemini Vision (só fotos)
            if record.media_type == MediaType.PHOTO:
                from backend.modules.m1_ingestion.gemini_analyzer import GeminiAnalyzer
                ai_data = GeminiAnalyzer().analyze(file_path)
                record.ai_description    = ai_data.get("ai_description")
                record.ai_people_count   = ai_data.get("ai_people_count")
                record.ai_setting        = ai_data.get("ai_setting")
                record.ai_emotion        = ai_data.get("ai_emotion")
                record.ai_tags           = ai_data.get("ai_tags")
                record.ai_narrative_hint = ai_data.get("ai_narrative_hint")

            # OCR (documentos)
            if record.media_type == MediaType.DOCUMENT:
                from backend.modules.m1_ingestion.ocr_extractor import OCRExtractor
                record.ocr_text = OCRExtractor().extract(file_path)

            record.status = ProcessingStatus.COMPLETED
            log.info("background_processing_done", id=record_id, file=original_filename)

        except Exception as e:
            log.error("background_processing_failed", id=record_id, error=str(e))
            record.status = ProcessingStatus.FAILED
            record.error_message = str(e)

        await db.commit()


def _get_dest_folder(ext: str) -> Path:
    if ext in {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff"}:
        return settings.RAW_DIR / "photos"
    elif ext in {".mp4", ".mov", ".avi"}:
        return settings.RAW_DIR / "videos"
    elif ext in {".ged", ".gedcom"}:
        return settings.RAW_DIR / "gedcom"
    return settings.RAW_DIR / "documents"


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo não suportado: {ext}")

    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_folder = _get_dest_folder(ext)
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_path = dest_folder / unique_name

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(await file.read())

    # Detecta tipo MIME
    import mimetypes
    mime, _ = mimetypes.guess_type(file.filename)
    from backend.modules.m1_ingestion.processor import MIME_TO_TYPE
    media_type = MIME_TO_TYPE.get(mime, MediaType.DOCUMENT)

    # Cria registo imediatamente com status PROCESSING
    record = MediaFile(
        original_filename = file.filename,
        stored_filename   = unique_name,
        file_path         = str(dest_path),
        file_size         = dest_path.stat().st_size,
        mime_type         = mime,
        media_type        = media_type,
        status            = ProcessingStatus.PROCESSING,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Agenda processamento em background — resposta já foi enviada
    background_tasks.add_task(
        process_in_background,
        dest_path,
        file.filename,
        record.id
    )

    log.info("upload_accepted", id=record.id, file=file.filename)

    return UploadResponse(
        message    = "Ficheiro recebido — a processar em background",
        file_id    = record.id,
        filename   = file.filename,
        media_type = record.media_type,
        status     = record.status,
    )


@router.post("/upload/batch", response_model=list[UploadResponse])
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload múltiplo — resposta imediata, Gemini processa em background."""
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Máximo 50 ficheiros")

    import mimetypes
    from backend.modules.m1_ingestion.processor import MIME_TO_TYPE

    results = []

    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue

        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest_folder = _get_dest_folder(ext)
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / unique_name

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(await file.read())

        mime, _ = mimetypes.guess_type(file.filename)
        media_type = MIME_TO_TYPE.get(mime, MediaType.DOCUMENT)

        record = MediaFile(
            original_filename = file.filename,
            stored_filename   = unique_name,
            file_path         = str(dest_path),
            file_size         = dest_path.stat().st_size,
            mime_type         = mime,
            media_type        = media_type,
            status            = ProcessingStatus.PROCESSING,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        background_tasks.add_task(
            process_in_background,
            dest_path,
            file.filename,
            record.id
        )

        results.append(UploadResponse(
            message    = "a processar em background",
            file_id    = record.id,
            filename   = file.filename,
            media_type = media_type,
            status     = ProcessingStatus.PROCESSING,
        ))

    log.info("batch_accepted", total=len(results))
    return results


@router.get("/media/{file_id}", response_model=MediaFileResponse)
async def get_media(file_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(MediaFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return record


@router.get("/media/{file_id}/status")
async def get_status(file_id: int, db: AsyncSession = Depends(get_db)):
    """Verifica se o processamento em background terminou."""
    record = await db.get(MediaFile, file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Não encontrado")
    return {
        "id":     record.id,
        "status": record.status,
        "ready":  record.status == ProcessingStatus.COMPLETED,
    }


@router.get("/media", response_model=list[MediaFileResponse])
async def list_media(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MediaFile).order_by(MediaFile.created_at.desc())
    )
    return result.scalars().all()
