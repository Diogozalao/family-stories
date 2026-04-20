"""
Módulo 4 — Geração Multimédia.

Orquestra:
1. Recolha de fotografias do M1 (ordenadas cronologicamente)
2. Geração de narração TTS a partir da história do M3
3. Montagem do vídeo documentário com efeito Ken Burns
4. Persistência do resultado na BD
"""

import uuid
import asyncio
import structlog
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.models.narrative import Story
from backend.models.video import VideoOutput, VideoStatus
from backend.modules.m4_multimedia.tts_generator import TTSGenerator
from backend.modules.m4_multimedia import video_builder

log = structlog.get_logger()


class M4Processor:

    def __init__(self):
        self.tts = TTSGenerator(lang="pt")
        (settings.PROCESSED_DIR / "audio").mkdir(parents=True, exist_ok=True)
        (settings.PROCESSED_DIR / "videos").mkdir(parents=True, exist_ok=True)

    async def generate_video(self, story_id: int, db: AsyncSession) -> VideoOutput:
        """
        Gera o vídeo documentário para uma história.
        Devolve o registo VideoOutput persistido na BD.
        """
        # Verifica se já existe um vídeo para esta história
        existing = await db.execute(
            select(VideoOutput).where(
                VideoOutput.story_id == story_id,
                VideoOutput.status == VideoStatus.COMPLETED,
            )
        )
        if vid := existing.scalar_one_or_none():
            if Path(vid.file_path).exists():
                log.info("m4_reuse", story_id=story_id, file=vid.filename)
                return vid

        # Cria registo de estado "a processar"
        record = VideoOutput(story_id=story_id, status=VideoStatus.PROCESSING)
        db.add(record)
        await db.commit()
        await db.refresh(record)

        try:
            result = await self._run(story_id, db)

            record.filename    = result["filename"]
            record.file_path   = result["file_path"]
            record.file_size_mb = result["size_mb"]
            record.photos_used = result["photos_used"]
            record.status      = VideoStatus.COMPLETED
            await db.commit()
            await db.refresh(record)
            return record

        except Exception as e:
            log.error("m4_failed", story_id=story_id, error=str(e))
            record.status        = VideoStatus.FAILED
            record.error_message = str(e)
            await db.commit()
            raise

    async def _run(self, story_id: int, db: AsyncSession) -> dict:
        story = await db.get(Story, story_id)
        if not story:
            raise ValueError(f"História {story_id} não encontrada")

        # Fotografias ordenadas cronologicamente
        q = await db.execute(
            select(MediaFile).where(
                MediaFile.status == ProcessingStatus.COMPLETED,
                MediaFile.media_type == MediaType.PHOTO,
            ).order_by(MediaFile.date_taken.asc().nulls_last(), MediaFile.created_at)
        )
        photos = q.scalars().all()
        photo_paths = [Path(p.file_path) for p in photos if Path(p.file_path).exists()]

        if not photo_paths:
            raise ValueError(
                "Sem fotografias disponíveis. Faz upload de fotos primeiro "
                "e certifica-te que o processamento M1 foi concluído."
            )

        # Legendas: data + local por fotografia
        captions = []
        for p in photos:
            if not Path(p.file_path).exists():
                continue
            parts = []
            if p.date_taken:
                parts.append(p.date_taken.strftime("%d/%m/%Y"))
            if p.ai_setting:
                parts.append(p.ai_setting)
            captions.append(" · ".join(parts))

        run_id    = uuid.uuid4().hex[:8]
        audio_dir = settings.PROCESSED_DIR / "audio" / run_id
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / "narration.mp3"
        video_path = settings.PROCESSED_DIR / "videos" / f"documentario_{story_id}_{run_id}.mp4"

        # TTS — corre em thread para não bloquear o event loop
        loop = asyncio.get_event_loop()
        log.info("m4_tts", story_id=story_id, chars=len(story.narrative))
        await loop.run_in_executor(None, self.tts.generate, story.narrative, audio_path)

        # Vídeo
        log.info("m4_video", story_id=story_id, photos=len(photo_paths))
        await loop.run_in_executor(
            None,
            video_builder.build_slideshow,
            photo_paths,
            audio_path,
            video_path,
            story.title,
            captions,
            None,   # sem música de fundo por omissão
        )

        # Limpa áudio temporário
        try:
            import shutil
            shutil.rmtree(audio_dir, ignore_errors=True)
        except Exception:
            pass

        size_mb = round(video_path.stat().st_size / 1024 / 1024, 2)
        return {
            "filename":    video_path.name,
            "file_path":   str(video_path),
            "photos_used": len(photo_paths),
            "size_mb":     size_mb,
        }
