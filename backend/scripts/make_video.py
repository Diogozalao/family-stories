"""Render a documentary video LOCALLY for an existing story.

Why this exists
---------------
The deployed backend runs on the free cloud tier (512 MB RAM), which runs out
of memory assembling a 720p video — so videos started from the web app fail or
get stuck on "A processar". This script renders the video on YOUR machine
instead (plenty of RAM), at full quality, and uploads the finished MP4 to the
SAME Supabase Storage the deployed app reads from. The video then shows up in
the web app automatically — no server to run, no tunnel.

Setup (once)
------------
    * ffmpeg installed and on PATH:        ffmpeg -version
    * the repo's .env points at Supabase   (already the case for local dev)

Usage
-----
    # List your stories and which ones still need a video
    python -m backend.scripts.make_video --list

    # Render the video for one story
    python -m backend.scripts.make_video --story 42

    # Render videos for every story that doesn't have one yet
    python -m backend.scripts.make_video --all
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import delete, select

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
# Register every model so cross-table foreign keys (video → story → project)
# resolve — same set the app loads at startup. Importing a subset leaves the
# SQLAlchemy metadata incomplete and flushes fail on the missing 'projects'.
from backend.models.media import MediaFile                  # noqa: F401
from backend.models.narrative import Story
from backend.models.project import Project, ProjectMedia    # noqa: F401
from backend.models.task import TaskRecord                  # noqa: F401
from backend.models.timeline import Person, TimelineEvent   # noqa: F401
from backend.models.video import VideoOutput, VideoStatus
from backend.modules.m4_multimedia.processor import M4Processor


async def _completed_story_ids(db) -> set[int]:
    rows = (await db.execute(
        select(VideoOutput.story_id).where(VideoOutput.status == VideoStatus.COMPLETED)
    )).scalars().all()
    return set(rows)


async def cmd_list() -> int:
    async with AsyncSessionLocal() as db:
        stories = (await db.execute(select(Story).order_by(Story.id))).scalars().all()
        if not stories:
            print("No stories yet — generate one in the app first.")
            return 0
        done = await _completed_story_ids(db)
        print(f"{'ID':>4}  {'VIDEO':<7}  TITLE")
        print("-" * 64)
        for s in stories:
            mark = "ok" if s.id in done else "-"
            print(f"{s.id:>4}  {mark:<7}  {s.title or '(untitled)'}")
        print(f"\nOutput resolution: {settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT} @ {settings.VIDEO_FPS}fps")
    return 0


async def _render(story_id: int) -> bool:
    """Render one story in its own session so a failure can't poison others."""
    async with AsyncSessionLocal() as db:
        story = (await db.execute(
            select(Story).where(Story.id == story_id)
        )).scalar_one_or_none()
        if not story:
            print(f"  story {story_id}: not found")
            return False

        # Clear any leftover stuck/failed rows from earlier cloud attempts so
        # the listing doesn't accumulate ghost "A processar" videos.
        await db.execute(delete(VideoOutput).where(
            VideoOutput.story_id == story_id,
            VideoOutput.status != VideoStatus.COMPLETED,
        ))
        await db.commit()

        print(f"  story {story_id}: rendering \"{story.title or '(untitled)'}\" ...")
        try:
            record = await M4Processor().generate_video(story_id, db, user_id=story.user_id)
        except Exception as exc:                      # noqa: BLE001 — report & continue
            print(f"  story {story_id}: FAILED — {exc}")
            return False
        print(f"  story {story_id}: done — {record.filename} "
              f"({record.file_size_mb} MB, {record.photos_used} photos) → uploaded to Supabase")
        return True


async def cmd_one(story_id: int) -> int:
    ok = await _render(story_id)
    return 0 if ok else 1


async def cmd_all() -> int:
    async with AsyncSessionLocal() as db:
        stories = (await db.execute(select(Story).order_by(Story.id))).scalars().all()
        done = await _completed_story_ids(db)
    todo = [s.id for s in stories if s.id not in done]
    if not todo:
        print("Every story already has a video — nothing to do.")
        return 0
    print(f"Rendering {len(todo)} video(s): {todo}")
    failures = 0
    for sid in todo:
        if not await _render(sid):
            failures += 1
    print(f"\nFinished: {len(todo) - failures} ok, {failures} failed.")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="List stories and their video status")
    g.add_argument("--story", type=int, metavar="ID", help="Render the video for one story")
    g.add_argument("--all", action="store_true", help="Render videos for all stories missing one")
    args = ap.parse_args()

    if args.list:
        return asyncio.run(cmd_list())
    if args.story is not None:
        return asyncio.run(cmd_one(args.story))
    return asyncio.run(cmd_all())


if __name__ == "__main__":
    sys.exit(main())
