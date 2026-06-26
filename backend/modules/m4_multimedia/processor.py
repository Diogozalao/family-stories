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
        # Photos are scoped to the SAME area as the story: a project story
        # uses only that project's photos, a global story only global ones —
        # keeping the documentary isolated, exactly like the narrative was.
        photo_stmt = (
            select(MediaFile)
            .where(
                MediaFile.user_id    == user_id,
                MediaFile.status     == ProcessingStatus.COMPLETED,
                MediaFile.media_type == MediaType.PHOTO,
            )
            .order_by(MediaFile.date_taken.asc().nulls_last(), MediaFile.created_at)
        )
        if story.project_id is not None:
            photo_stmt = photo_stmt.where(MediaFile.project_id == story.project_id)
        else:
            photo_stmt = photo_stmt.where(MediaFile.project_id.is_(None))
        photos = (await db.execute(photo_stmt)).scalars().all()

        # Use ONLY the photos this story was generated from (the user's wizard
        # selection), so the documentary mirrors the story — just like the
        # narrative did. Order is preserved as selected. Legacy stories have no
        # selection → keep every scope photo (previous behaviour).
        selected = list(getattr(story, "media_ids", None) or [])
        if selected:
            rank = {mid: i for i, mid in enumerate(selected)}
            chosen = [p for p in photos if p.id in rank]
            if chosen:
                photos = sorted(chosen, key=lambda p: rank[p.id])
        if not photos:
            raise ValueError(
                "No photos available. Upload photos first and make sure the "
                "M1 processing pipeline finished successfully."
            )

        run_id = uuid.uuid4().hex[:8]
        work   = Path(tempfile.mkdtemp(prefix=f"m4_{run_id}_"))
        photos_dir   = work / "photos"
        audio_dir    = work / "audio"
        audio_path   = work / "narration.mp3"
        video_name   = f"documentario_{story_id}_{run_id}.mp4"
        video_local  = work / video_name
        photos_dir.mkdir()
        audio_dir.mkdir()

        try:
            loop = asyncio.get_event_loop()

            # Pick the TTS voice that matches the language the LLM wrote the
            # story in. ``story.language`` was captured at narrative-generation
            # time so the documentary keeps the same language even if the user
            # later flips the UI toggle.
            story_language = (getattr(story, "language", None) or "pt").lower()
            # Narrator gender the user picked for this story (male/female).
            story_voice = getattr(story, "voice", None)
            tts = TTSGenerator(language=story_language, voice=story_voice)

            # Per-id download cache so a photo referenced by one scene is
            # only fetched from Storage once.
            downloaded: dict[int, Path] = {}

            async def _fetch(media) -> Path | None:
                if media.id in downloaded:
                    return downloaded[media.id]
                if not media.file_path:
                    return None
                local = photos_dir / f"{media.id}_{Path(media.file_path).name}"
                try:
                    await download_to_disk(media.file_path, local)
                except Exception as exc:
                    log.warning("m4_photo_fetch_failed", key=media.file_path, error=str(exc))
                    return None
                downloaded[media.id] = local
                return local

            # ── Scene-based path (preferred) ────────────────────────────
            # When the story carries a scene breakdown, build a documentary
            # that shows each photo exactly while its narration plays.
            scenes = getattr(story, "scenes", None)
            if scenes:
                assembly = await self._build_scene_assembly(
                    scenes, {p.id: p for p in photos}, _fetch, audio_dir, tts, loop)
                if assembly:
                    used = sum(len(s["photo_paths"]) for s in assembly)
                    want_subs = bool(getattr(story, "subtitles", True))
                    log.info("m4_scene_mode", story_id=story_id,
                             scenes=len(assembly), photos=used, subtitles=want_subs)
                    await loop.run_in_executor(
                        None, video_builder.build_documentary,
                        assembly, video_local, story.title, None, want_subs)
                    return await self._finalize(user_id, video_name, video_local, used)
                log.info("m4_scene_empty_fallback", story_id=story_id)

            # ── Legacy even-split slideshow (fallback) ──────────────────
            photo_paths: list[Path] = []
            captions:    list[str]  = []
            for photo in photos:
                local = await _fetch(photo)
                if not local:
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

            log.info("m4_tts", story_id=story_id, chars=len(story.narrative),
                     language=story_language, voice=tts.voice)
            await loop.run_in_executor(None, tts.generate, story.narrative, audio_path)

            log.info("m4_video", story_id=story_id, photos=len(photo_paths))
            await loop.run_in_executor(
                None, video_builder.build_slideshow,
                photo_paths, audio_path, video_local, story.title, captions, None)

            return await self._finalize(user_id, video_name, video_local, len(photo_paths))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    async def _build_scene_assembly(self, scenes, photo_by_id, fetch, audio_dir, tts, loop):
        """Resolve scene photos, coalesce photo-less scenes and synthesise
        one narration clip per scene.

        Returns a list of ``{"audio_path", "photo_paths", "caption"}`` ready
        for :func:`video_builder.build_documentary`, or ``[]`` if nothing
        usable could be resolved (caller then falls back to the slideshow).
        """
        # 1) Resolve each scene's photos from Storage (skipping missing ones).
        resolved: list[dict] = []
        for scene in scenes:
            paths: list[Path] = []
            for pid in scene.get("photo_ids", []) or []:
                media = photo_by_id.get(pid)
                if media is None:
                    continue
                local = await fetch(media)
                if local:
                    paths.append(local)
            resolved.append({
                "text":    (scene.get("text") or "").strip(),
                "paths":   paths,
                "caption": scene.get("caption"),
            })

        # 2) Coalesce: a scene whose photos couldn't be resolved donates its
        #    narration text to the next scene that has photos, so no prose is
        #    lost and every rendered scene has something to show.
        merged: list[dict] = []
        carry = ""
        for r in resolved:
            if r["paths"]:
                text = f"{carry} {r['text']}".strip() if carry else r["text"]
                merged.append({"text": text, "paths": r["paths"], "caption": r["caption"]})
                carry = ""
            else:
                carry = f"{carry} {r['text']}".strip() if carry else r["text"]
        if carry and merged:
            merged[-1]["text"] = f"{merged[-1]['text']} {carry}".strip()

        if not merged:
            return []

        # 3) One narration MP3 per scene.
        assembly: list[dict] = []
        for index, scene in enumerate(merged):
            if not scene["text"]:
                continue
            audio_path = audio_dir / f"scene_{index:02d}.mp3"
            await loop.run_in_executor(None, tts.generate, scene["text"], audio_path)
            assembly.append({
                "audio_path":  audio_path,
                "photo_paths": scene["paths"],
                "caption":     scene["caption"],
                # The narration prose for this scene — burned in as subtitles
                # (split across the scene's photos) by ``build_documentary``.
                "text":        scene["text"],
            })
        return assembly

    async def _finalize(self, user_id, video_name: str, video_local: Path, photos_used: int) -> dict:
        """Upload the rendered MP4 to Storage and return the DB pointer dict."""
        video_key = object_key_for(user_id, "videos", video_name)
        await upload_bytes(video_key, video_local.read_bytes(), content_type="video/mp4")
        size_mb = round(video_local.stat().st_size / 1024 / 1024, 2)
        return {
            "filename":    video_name,
            "file_path":   video_key,
            "photos_used": photos_used,
            "size_mb":     size_mb,
        }
