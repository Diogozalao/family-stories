import uuid
import aiofiles
import structlog
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from backend.core.config import settings
from backend.core.database import get_db
from backend.models.media import MediaFile
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

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Valida extensão
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de ficheiro não suportado: {ext}"
        )

    # Nome único para evitar colisões
    unique_name = f"{uuid.uuid4().hex}{ext}"
    
    # Determina pasta de destino
    if ext in {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff"}:
        dest_folder = settings.RAW_DIR / "photos"
    elif ext in {".mp4", ".mov", ".avi"}:
        dest_folder = settings.RAW_DIR / "videos"
    elif ext in {".ged", ".gedcom"}:
        dest_folder = settings.RAW_DIR / "gedcom"
    else:
        dest_folder = settings.RAW_DIR / "documents"

    dest_folder.mkdir(parents=True, exist_ok=True)
    dest_path = dest_folder / unique_name

    # Guarda ficheiro em disco
    async with aiofiles.open(dest_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    log.info("file_saved", filename=file.filename, path=str(dest_path))

    # Processa com M1
    record = await processor.process(
        file_path=dest_path,
        original_filename=file.filename,
        db=db
    )

    return UploadResponse(
        message="Ficheiro recebido e processado com sucesso",
        file_id=record.id,
        filename=file.filename,
        media_type=record.media_type,
        status=record.status,
    )


@router.get("/media/{file_id}", response_model=MediaFileResponse)
async def get_media(file_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MediaFile).where(MediaFile.id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Ficheiro não encontrado")
    return record


@router.get("/media", response_model=list[MediaFileResponse])
async def list_media(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MediaFile).order_by(MediaFile.created_at.desc()))
    return result.scalars().all()


@router.post("/upload/batch", response_model=list[UploadResponse])
async def upload_multiple_files(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload de múltiplos ficheiros em simultâneo."""
    if len(files) > 50:
        raise HTTPException(
            status_code=400,
            detail="Máximo de 50 ficheiros por batch"
        )

    results = []
    errors  = []

    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{file.filename}: tipo não suportado")
            continue

        unique_name = f"{uuid.uuid4().hex}{ext}"

        if ext in {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tiff"}:
            dest_folder = settings.RAW_DIR / "photos"
        elif ext in {".mp4", ".mov", ".avi"}:
            dest_folder = settings.RAW_DIR / "videos"
        elif ext in {".ged", ".gedcom"}:
            dest_folder = settings.RAW_DIR / "gedcom"
        else:
            dest_folder = settings.RAW_DIR / "documents"

        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / unique_name

        async with aiofiles.open(dest_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        record = await processor.process(
            file_path=dest_path,
            original_filename=file.filename,
            db=db
        )

        results.append(UploadResponse(
            message   = "processado com sucesso",
            file_id   = record.id,
            filename  = file.filename,
            media_type= record.media_type,
            status    = record.status,
        ))
        log.info("batch_file_done", filename=file.filename, id=record.id)

    if errors:
        log.warning("batch_upload_errors", errors=errors)

    return results
