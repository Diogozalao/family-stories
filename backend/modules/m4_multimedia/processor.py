"""Module 4 — Multimedia generation orchestrator.

Ties together:
    1. Photo selection from M1 (chronologically ordered, completed only).
    2. TTS narration of the M3 story.
    3. Video assembly via ``video_builder``.
    4. Persistence of the resulting ``VideoOutput`` record.
"""

import asyncio
import shutil
import uuid
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.models.narrative import Story
from backend.models.video import VideoOutput, VideoStatus
from backend.modules.m4_multimedia import video_builder
from backend.modules.m4_multimedia.tts_generator import TTSGenerator

log = structlog.get_logger()


class M4Processor:
    """Coordinate narration, video assembly and persistence for a story."""

    def __init__(self):
        self.tts = TTSGenerator(lang="pt", tld="pt")
        (settings.PROCESSED_DIR / "audio").mkdir(parents=True, exist_ok=True)
        (settings.PROCESSED_DIR / "videos").mkdir(parents=True, exist_ok=True)

    async def generate_video(self, story_id: int, db: AsyncSession) -> VideoOutput:
        """Generate the documentary for ``story_id`` and persist the result.

        If a completed video already exists on disk for this story, it is
        reused instead of rebuilt.
        """
        existing = await db.execute(
            select(VideoOutput).where(
                VideoOutput.story_id == story_id,
                VideoOutput.status   == VideoStatus.COMPLETED,
            )
        )
        cached = existing.scalar_one_or_none()
        if cached and cached.file_path and Path(cached.file_path).exists():
            log.info("m4_reuse", story_id=story_id, file=cached.filename)
            return cached

        # Carry the project linkage from the source story so the video
        # appears under the same project workspace in the UI.
        story = await db.get(Story, story_id)
        record = VideoOutput(
            story_id   = story_id,
            project_id = story.project_id if story else None,
            status     = VideoStatus.PROCESSING,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        try:
            result = await self._run(story_id, db)

            record.filename     = result["filename"]
            record.file_path    = result["file_path"]
            record.file_size_mb = result["size_mb"]
            record.photos_used  = result["photos_used"]
            record.status       = VideoStatus.COMPLETED
            await db.commit()
            await db.refresh(record)
            return record

        except Exception as exc:
            log.error("m4_failed", story_id=story_id, error=str(exc))
            record.status        = VideoStatus.FAILED
            record.error_message = str(exc)
            await db.commit()
            raise

    async def _run(self, story_id: int, db: AsyncSession) -> dict:
        """Do the actual narration + video assembly work for a story."""
        story = await db.get(Story, story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        # Pick every completed photo, oldest first; photos with no date go last.
        query = await db.execute(
            select(MediaFile)
            .where(
                MediaFile.status     == ProcessingStatus.COMPLETED,
                MediaFile.media_type == MediaType.PHOTO,
            )
            .order_by(MediaFile.date_taken.asc().nulls_last(), MediaFile.created_at)
        )
        photos = query.scalars().all()
        photo_paths = [Path(p.file_path) for p in photos if Path(p.file_path).exists()]

        if not photo_paths:
            raise ValueError(
                "No photos available. Upload photos first and make sure the "
                "M1 processing pipeline finished successfully."
            )

        # Caption each photo with its date and setting (whatever is available).
        captions: list[str] = []
        for photo in photos:
            if not Path(photo.file_path).exists():
                continue
            parts: list[str] = []
            if photo.date_taken:
                parts.append(photo.date_taken.strftime("%d/%m/%Y"))
            if photo.ai_setting:
                parts.append(photo.ai_setting)
            captions.append(" · ".join(parts))

        run_id     = uuid.uuid4().hex[:8]
        audio_dir  = settings.PROCESSED_DIR / "audio"  / run_id
        audio_path = audio_dir / "narration.mp3"
        video_path = settings.PROCESSED_DIR / "videos" / f"documentario_{story_id}_{run_id}.mp4"
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Both TTS and video rendering are CPU/IO-heavy and would block the
        # event loop — offload them to the default thread pool.
        loop = asyncio.get_event_loop()

        log.info("m4_tts", story_id=story_id, chars=len(story.narrative))
        await loop.run_in_executor(None, self.tts.generate, story.narrative, audio_path)

        log.info("m4_video", story_id=story_id, photos=len(photo_paths))
        await loop.run_in_executor(
            None,
            video_builder.build_slideshow,
            photo_paths,
            audio_path,
            video_path,
            story.title,
            captions,
            None,   # No background music by default.
        )

        # Remove the intermediate narration audio — keep the videos folder tidy.
        shutil.rmtree(audio_dir, ignore_errors=True)

        size_mb = round(video_path.stat().st_size / 1024 / 1024, 2)
        return {
            "filename":    video_path.name,
            "file_path":   str(video_path),
            "photos_used": len(photo_paths),
            "size_mb":     size_mb,
        }
