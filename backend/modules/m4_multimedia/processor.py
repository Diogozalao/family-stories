"""Module 4 — Multimedia generation orchestrator.

Ties together:
    1. Photo selection from M1 (chronologically ordered, completed only).
    2. TTS narration of the M3 story.
    3. Video assembly via ``video_builder``.
    4. Persistence of the resulting ``VideoOutput`` record.
"""

import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.supabase_storage import download_to_disk, object_key_for, upload_bytes
from backend.models.media import MediaFile, MediaType, ProcessingStatus
from backend.models.narrative import Story
from backend.models.video import VideoOutput, VideoStatus
from backend.modules.m4_multimedia import video_builder
from backend.modules.m4_multimedia.tts_generator import TTSGenerator

log = structlog.get_logger()


class M4Processor:
    """Coordinate narration, video assembly and persistence for a story.

    Reads source photos from Supabase Storage into a per-run temp dir,
    builds the slideshow + narration there, and uploads the resulting
    MP4 back to Storage under ``{user_id}/videos/{filename}``. No state
    is kept on the local filesystem between runs.
    """

    def __init__(self):
        # Default to Portuguese; ``_run`` instantiates a fresh ``TTSGenerator``
        # per call once it knows the language the story was written in.
        self.tts = TTSGenerator(language="pt")

    async def generate_video(self, story_id: int, db: AsyncSession, user_id) -> VideoOutput:
        """Generate the documentary for ``story_id`` and persist the result.

        ``user_id`` must match the owner of ``story_id`` — we resolve the
        story under that constraint up front so we never let one user
        trigger work over another user's story.
        """
        story = (await db.execute(
            select(Story).where(Story.id == story_id, Story.user_id == user_id)
        )).scalar_one_or_none()
        if not story:
            raise ValueError(f"Story {story_id} not found")

        existing = await db.execute(
            select(VideoOutput).where(
                VideoOutput.story_id == story_id,
                VideoOutput.user_id  == user_id,
                VideoOutput.status   == VideoStatus.COMPLETED,
            )
        )
        cached = existing.scalar_one_or_none()
        if cached and cached.file_path and Path(cached.file_path).exists():
            log.info("m4_reuse", story_id=story_id, file=cached.filename)
            return cached

        record = VideoOutput(
            user_id    = user_id,
            story_id   = story_id,
            project_id = story.project_id,
            status     = VideoStatus.PROCESSING,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        try:
            result = await self._run(story_id, db, user_id, story)

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

    async def _run(self, story_id: int, db: AsyncSession, user_id, story: Story) -> dict:
        """Do the actual narration + video assembly work for a story.

        Source photos and the rendered video both live in Supabase
        Storage; this method touches the local disk only for ephemeral
        scratch space (a temp dir cleaned up before returning).
        """
        query = await db.execute(
            select(MediaFile)
            .where(
                MediaFile.user_id    == user_id,
                MediaFile.status     == ProcessingStatus.COMPLETED,
                MediaFile.media_type == MediaType.PHOTO,
            )
            .order_by(MediaFile.date_taken.asc().nulls_last(), MediaFile.created_at)
        )
        photos = query.scalars().all()
        if not photos:
            raise ValueError(
                "No photos available. Upload photos first and make sure the "
                "M1 processing pipeline finished successfully."
            )

        run_id = uuid.uuid4().hex[:8]
        work   = Path(tempfile.mkdtemp(prefix=f"m4_{run_id}_"))
        photos_dir   = work / "photos"
        audio_path   = work / "narration.mp3"
        video_name   = f"documentario_{story_id}_{run_id}.mp4"
        video_local  = work / video_name
        photos_dir.mkdir()

        try:
            # Pull each source photo from Storage into the scratch dir.
            photo_paths: list[Path] = []
            captions:    list[str]  = []
            for photo in photos:
                if not photo.file_path:
                    continue
                local = photos_dir / Path(photo.file_path).name
                try:
                    await download_to_disk(photo.file_path, local)
                except Exception as exc:
                    log.warning("m4_photo_fetch_failed", key=photo.file_path, error=str(exc))
                    continue
                photo_paths.append(local)
                parts: list[str] = []
                if photo.date_taken:
                    parts.append(photo.date_taken.strftime("%d/%m/%Y"))
                if photo.ai_setting:
                    parts.append(photo.ai_setting)
                captions.append(" · ".join(parts))

            if not photo_paths:
                raise ValueError("Falha ao obter fotografias do Storage para montar o vídeo.")

            loop = asyncio.get_event_loop()

            # Pick the TTS voice that matches the language the LLM wrote the
            # story in. ``story.language`` was captured at narrative-generation
            # time so the documentary keeps the same language even if the user
            # later flips the UI toggle.
            story_language = (getattr(story, "language", None) or "pt").lower()
            tts = TTSGenerator(language=story_language)

            log.info("m4_tts", story_id=story_id, chars=len(story.narrative),
                     language=story_language, voice=tts.voice)
            await loop.run_in_executor(None, tts.generate, story.narrative, audio_path)

            log.info("m4_video", story_id=story_id, photos=len(photo_paths))
            await loop.run_in_executor(
                None,
                video_builder.build_slideshow,
                photo_paths,
                audio_path,
                video_local,
                story.title,
                captions,
                None,    # No background music by default.
            )

            # Push the finished MP4 to Storage and keep the object key as
            # the canonical "where the video lives" pointer in the DB.
            video_key = object_key_for(user_id, "videos", video_name)
            await upload_bytes(video_key, video_local.read_bytes(), content_type="video/mp4")
            size_mb = round(video_local.stat().st_size / 1024 / 1024, 2)

            return {
                "filename":    video_name,
                "file_path":   video_key,
                "photos_used": len(photo_paths),
                "size_mb":     size_mb,
            }
        finally:
            shutil.rmtree(work, ignore_errors=True)
