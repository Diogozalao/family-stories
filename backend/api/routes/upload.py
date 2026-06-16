"""Upload routes for photos and generic media files.

Each upload is validated (size, MIME, magic bytes) before the bytes are
written to disk. Accepted files are routed to the M1 ingestion pipeline
straight away; the HTTP response is returned as soon as the file is
persisted and registered, while any heavy AI work can run in a
background task downstream.

Every row this module touches in ``media_files`` is scoped to the
authenticated ``user.id`` — the backend connects to Postgres as the
``postgres`` role (which bypasses RLS), so we cannot rely on the
database to enforce isolation. The ``WHERE user_id = ...`` filter on
every query and the ``user_id = ...`` assignment on every insert IS the
isolation layer.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user, get_current_user_query_or_header
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.core.supabase_storage import (
    cached_signed_url,
    create_signed_url,
    delete_object,
    invalidate_signed_url,
)
from backend.core.upload_validator import validate_photo
from backend.models.media import MediaFile, ProcessingStatus
from backend.modules.m1_ingestion.processor import M1Processor
from backend.schemas.media import MediaFileResponse, UploadResponse

router    = APIRouter(prefix="/api/v1", tags=["upload"])
log       = structlog.get_logger()
processor = M1Processor()

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tiff"}
MAX_BATCH_FILES  = 50


async def _ingest(file: UploadFile, content: bytes, db: AsyncSession, user_id) -> MediaFile:
    """Hand validated bytes off to M1.

    Runs only the fast part in-request (security scan, EXIF, Storage upload)
    and schedules the slow AI analysis (Gemini Vision / OCR) to run in the
    background, so the upload returns quickly and the photo is immediately
    viewable. The row stays ``PROCESSING`` until the analysis completes.
    """
    record = await processor.process(
        content           = content,
        original_filename = file.filename,
        db                = db,
        user_id           = user_id,
        defer_ai          = True,
    )
    # Only schedule analysis when the fast part left the row PROCESSING —
    # a row that failed the security scan has nothing left to analyse.
    if record.status == ProcessingStatus.PROCESSING:
        from backend.tasks.bodies import analyze_media_body
        from backend.tasks.inproc import submit
        media_id = record.id
        submit(lambda: analyze_media_body(media_id, user_id), label=f"analyze-media-{media_id}")
    return record


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
    record    = await _ingest(file, validated.content, db, user.id)

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
    """Upload up to ``MAX_BATCH_FILES`` photos in one request."""
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
            record    = await _ingest(file, validated.content, db, user.id)
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
async def get_media(
    file_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Return the M1 record for a specific file id — owned rows only."""
    result = await db.execute(
        select(MediaFile).where(MediaFile.id == file_id, MediaFile.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return record


class MediaPersonsRequest(BaseModel):
    """The full set of person ids that appear in a photo (replaces previous)."""
    person_ids: list[int] = []


@router.put("/media/{file_id}/persons", response_model=MediaFileResponse)
async def set_media_persons(
    file_id: int,
    payload: MediaPersonsRequest,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Tag which family members appear in a photo — owner only.

    Only ids of persons owned by the caller are kept, so a photo can never
    be linked to someone else's relatives.
    """
    from backend.models.timeline import Person

    record = (await db.execute(
        select(MediaFile).where(MediaFile.id == file_id, MediaFile.user_id == user.id)
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    valid = set((await db.execute(
        select(Person.id).where(Person.id.in_(payload.person_ids or []), Person.user_id == user.id)
    )).scalars().all())
    record.person_ids = [pid for pid in (payload.person_ids or []) if pid in valid]

    await db.commit()
    await db.refresh(record)
    log.info("media_persons_set", id=record.id, n=len(record.person_ids))
    return record


class MediaUpdateRequest(BaseModel):
    """Partial update of a media's user-editable metadata.

    ``date_taken`` accepts an ISO date (``YYYY-MM-DD``) to set the photo's
    date — essential for scans/screenshots that carry no EXIF date — or an
    empty value to clear it. Absent fields are left untouched.
    """
    date_taken:    Optional[str] = None
    location_name: Optional[str] = None


@router.patch("/media/{file_id}", response_model=MediaFileResponse)
async def update_media(
    file_id: int,
    payload: MediaUpdateRequest,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Edit a photo's date and/or location — owned rows only.

    Lets the user supply a real date for material without EXIF. The linked
    timeline event is re-synced on the next ``/timeline/build`` (which the
    frontend triggers right after).
    """
    record = (await db.execute(
        select(MediaFile).where(MediaFile.id == file_id, MediaFile.user_id == user.id)
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    fields = payload.model_dump(exclude_unset=True)
    if "date_taken" in fields:
        raw = (fields["date_taken"] or "").strip()
        if raw:
            try:
                record.date_taken = datetime.fromisoformat(raw)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de data inválido (usa AAAA-MM-DD).")
        else:
            record.date_taken = None
    if "location_name" in fields:
        record.location_name = (fields["location_name"] or "").strip() or None

    await db.commit()
    await db.refresh(record)
    log.info("media_updated", id=record.id, date_taken=str(record.date_taken))
    return record


@router.get("/media", response_model=list[MediaFileResponse])
async def list_media(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Return every ingested media file owned by the caller, newest first."""
    result = await db.execute(
        select(MediaFile)
        .where(MediaFile.user_id == user.id)
        .order_by(MediaFile.created_at.desc())
    )
    return result.scalars().all()


@router.get("/media/{file_id}/url")
async def get_media_url(
    file_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Return a fresh signed URL for the photo in Supabase Storage.

    The frontend caches this JSON response via React Query so an ``<img>``
    that already loaded keeps its URL across navigations (no flicker, no
    re-download). We hand out URLs valid for an hour so the cache stays
    warm even on a multi-page session.
    """
    record = (await db.execute(
        select(MediaFile).where(MediaFile.id == file_id, MediaFile.user_id == user.id)
    )).scalar_one_or_none()
    if not record or not record.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    signed = await cached_signed_url(record.file_path, expires_in=3600)
    return {"url": signed, "expires_in": 3600}


@router.get("/media/{file_id}/file")
async def serve_media_bytes(
    file_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user_query_or_header),
):
    """Legacy ``<img>``/``<video>`` redirect endpoint.

    Kept around for ``<video>`` tags and direct browser links that can't
    call the JSON endpoint above. Issues a 302 to a fresh signed URL.
    """
    record = (await db.execute(
        select(MediaFile).where(MediaFile.id == file_id, MediaFile.user_id == user.id)
    )).scalar_one_or_none()
    if not record or not record.file_path:
        raise HTTPException(status_code=404, detail="File not found")

    signed = await cached_signed_url(record.file_path, expires_in=3600)
    return RedirectResponse(url=signed, status_code=302)


@router.delete("/media/{file_id}")
async def delete_media(
    file_id: int,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Remove a photo from Supabase Storage and the database — owned rows only."""
    record = (await db.execute(
        select(MediaFile).where(MediaFile.id == file_id, MediaFile.user_id == user.id)
    )).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if record.file_path:
        invalidate_signed_url(record.file_path)
        try:
            await delete_object(record.file_path)
        except Exception as exc:
            # Don't block the DB delete on a Storage hiccup — log loudly and
            # let the row go, otherwise we'd leak ghost objects.
            log.warning("storage_delete_swallowed", key=record.file_path, error=str(exc))
    await db.delete(record)
    await db.commit()
    return {"message": "Deleted"}
