"""Upload routes for photos and generic media files.

Each upload is validated (size, MIME, magic bytes) before the bytes are
written to disk. Accepted files are routed to the M1 ingestion pipeline
straight away; the HTTP response is returned as soon as the file is
persisted and registered, while any heavy AI work can run in a
background task downstream.
"""

import uuid
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user, get_current_user_query_or_header
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.core.upload_validator import validate_photo
from backend.models.media import MediaFile
from backend.models.user import User
from backend.modules.m1_ingestion.processor import M1Processor
from backend.schemas.media import MediaFileResponse, UploadResponse

router    = APIRouter(prefix="/api/v1", tags=["upload"])
log       = structlog.get_logger()
processor = M1Processor()

# Extensions accepted by the photo endpoints. MIME validation is the
# authoritative check — this set only prevents obviously wrong filenames
# from reaching the expensive magic-byte scan.
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tiff"}

MAX_BATCH_FILES = 50


async def _save_and_ingest(
    file:    UploadFile,
    content: bytes,
    db:      AsyncSession,
) -> MediaFile:
    """Persist validated bytes to ``data/raw/photos`` and run M1 ingestion."""
    ext = Path(file.filename).suffix.lower() or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_folder = settings.RAW_DIR / "photos"
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_path = dest_folder / unique_name

    async with aiofiles.open(dest_path, "wb") as fh:
        await fh.write(content)

    log.info("file_saved", filename=file.filename, path=str(dest_path), size=len(content))

    return await processor.process(
        file_path         = dest_path,
        original_filename = file.filename,
        db                = db,
    )


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_file(
    request: Request,
    file:    UploadFile = File(...),
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Upload a single photo for ingestion by M1."""
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension: {ext}. Accepted: {sorted(PHOTO_EXTENSIONS)}",
        )

    validated = await validate_photo(file)
    record    = await _save_and_ingest(file, validated.content, db)

    return UploadResponse(
        message    = "File received and processed successfully",
        file_id    = record.id,
        filename   = file.filename,
        media_type = record.media_type,
        status     = record.status,
    )


@router.post("/upload/batch", response_model=list[UploadResponse])
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_multiple_files(
    request: Request,
    files:   list[UploadFile] = File(...),
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Upload up to ``MAX_BATCH_FILES`` photos in one request.

    Bad files are skipped (not fatal) so a single broken photo does not
    prevent the rest of a batch from being ingested. Errors for skipped
    files are logged.
    """
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_BATCH_FILES} files per batch",
        )

    results: list[UploadResponse] = []
    errors:  list[str] = []

    for file in files:
        try:
            ext = Path(file.filename or "").suffix.lower()
            if ext and ext not in PHOTO_EXTENSIONS:
                errors.append(f"{file.filename}: unsupported extension {ext}")
                continue

            validated = await validate_photo(file)
            record    = await _save_and_ingest(file, validated.content, db)
            results.append(UploadResponse(
                message    = "Processed successfully",
                file_id    = record.id,
                filename   = file.filename,
                media_type = record.media_type,
                status     = record.status,
            ))
            log.info("batch_file_done", filename=file.filename, id=record.id)
        except HTTPException as exc:
            errors.append(f"{file.filename}: {exc.detail}")
        except Exception as exc:
            errors.append(f"{file.filename}: {exc}")
            log.error("batch_file_error", filename=file.filename, error=str(exc))

    if errors:
        log.warning("batch_upload_errors", count=len(errors), errors=errors)

    return results


@router.get("/media/{file_id}", response_model=MediaFileResponse)
async def get_media(file_id: int, db: AsyncSession = Depends(get_db)):
    """Return the M1 record for a specific file id."""
    result = await db.execute(select(MediaFile).where(MediaFile.id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@router.get("/media", response_model=list[MediaFileResponse])
async def list_media(db: AsyncSession = Depends(get_db)):
    """Return every ingested media file, newest first."""
    result = await db.execute(select(MediaFile).order_by(MediaFile.created_at.desc()))
    return result.scalars().all()


@router.get("/media/{file_id}/file")
async def serve_media_bytes(
    file_id: int,
    db:      AsyncSession = Depends(get_db),
    _user:   User         = Depends(get_current_user_query_or_header),
):
    """Stream the raw photo bytes — used by the frontend ``<img>`` tags.

    Accepts JWT either in ``Authorization`` header or in ``?token=`` query
    so that bare ``<img>`` tags (which can't set headers) still authenticate.
    """
    record = (await db.execute(select(MediaFile).where(MediaFile.id == file_id))).scalar_one_or_none()
    if not record or not record.file_path:
        raise HTTPException(status_code=404, detail="File not found")
    disk_path = Path(record.file_path)
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(str(disk_path), filename=record.original_filename)


@router.delete("/media/{file_id}")
async def delete_media(
    file_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Remove a photo both from disk and the database."""
    record = (await db.execute(select(MediaFile).where(MediaFile.id == file_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if record.file_path:
        disk_path = Path(record.file_path)
        if disk_path.exists():
            disk_path.unlink()
    await db.delete(record)
    await db.commit()
    return {"message": "Deleted"}
