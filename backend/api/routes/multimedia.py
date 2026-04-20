"""
Módulo 4 — Rotas de Geração Multimédia.

Endpoints:
    POST /api/v1/multimedia/generate/{story_id}   — gera vídeo documentário
    GET  /api/v1/multimedia/video/{filename}       — descarrega vídeo
    GET  /api/v1/multimedia/videos                 — lista todos os vídeos
    GET  /api/v1/multimedia/status/{video_id}      — estado de geração
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import get_db
from backend.models.video import VideoOutput, VideoStatus
from backend.modules.m4_multimedia.processor import M4Processor

router    = APIRouter(prefix="/api/v1/multimedia", tags=["multimédia"])
log       = structlog.get_logger()
processor = M4Processor()


@router.post("/generate/{story_id}")
async def generate_video(story_id: int, db: AsyncSession = Depends(get_db)):
    """
    Gera o vídeo documentário para uma história.

    Fluxo:
    1. Busca a narrativa do M3 (story_id)
    2. Gera narração TTS com gTTS
    3. Monta vídeo com Ken Burns + sincronização
    4. Guarda em data/processed/videos/
    5. Retorna URL para download

    Demora 1-5 minutos dependendo do número de fotos.
    """
    try:
        record = await processor.generate_video(story_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("m4_api_error", story_id=story_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Erro na geração do vídeo: {str(e)}")

    return {
        "message":     "Vídeo gerado com sucesso",
        "video_id":    record.id,
        "story_id":    story_id,
        "filename":    record.filename,
        "size_mb":     record.file_size_mb,
        "photos_used": record.photos_used,
        "status":      record.status,
        "download_url": f"/api/v1/multimedia/video/{record.filename}",
    }


@router.get("/video/{filename}")
async def download_video(filename: str):
    """Descarrega o vídeo documentário gerado."""
    # Valida nome de ficheiro para evitar path traversal
    if "/" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nome de ficheiro inválido")

    video_path = settings.PROCESSED_DIR / "videos" / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/videos")
async def list_videos(db: AsyncSession = Depends(get_db)):
    """Lista todos os vídeos gerados."""
    result = await db.execute(
        select(VideoOutput).order_by(VideoOutput.created_at.desc())
    )
    videos = result.scalars().all()
    return [
        {
            "id":           v.id,
            "story_id":     v.story_id,
            "filename":     v.filename,
            "size_mb":      v.file_size_mb,
            "photos_used":  v.photos_used,
            "status":       v.status,
            "created_at":   str(v.created_at),
            "download_url": f"/api/v1/multimedia/video/{v.filename}" if v.filename else None,
        }
        for v in videos
    ]


@router.get("/status/{video_id}")
async def video_status(video_id: int, db: AsyncSession = Depends(get_db)):
    """Verifica o estado de um vídeo específico."""
    video = await db.get(VideoOutput, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Registo de vídeo não encontrado")
    return {
        "id":            video.id,
        "story_id":      video.story_id,
        "status":        video.status,
        "filename":      video.filename,
        "size_mb":       video.file_size_mb,
        "error_message": video.error_message,
        "created_at":    str(video.created_at),
    }


@router.delete("/videos/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Apaga um vídeo da BD e do disco."""
    video = await db.get(VideoOutput, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Não encontrado")

    if video.file_path:
        from pathlib import Path
        p = Path(video.file_path)
        if p.exists():
            p.unlink()

    await db.delete(video)
    await db.commit()
    return {"message": "Vídeo apagado com sucesso"}
