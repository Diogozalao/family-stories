"""Projetos / coleções — espaços de trabalho que agrupam fotos, histórias e vídeos.

Um ``Project`` é uma vista filtrada e curada sobre a Biblioteca global.
Toda a query/insert nesta route filtra/atribui por ``user.id`` — RLS
é bypassada porque o backend conecta como ``postgres``, portanto este
filtro **é** a barreira de isolamento entre utilizadores.
"""

from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.database import get_db
from backend.core.supabase_storage import delete_object
from backend.models.media import MediaFile
from backend.models.narrative import Story
from backend.models.project import Project, ProjectMedia
from backend.models.video import VideoOutput

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
log    = structlog.get_logger()


# ── Schemas ───────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name:        str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    name:           Optional[str] = Field(default=None, min_length=1, max_length=120)
    description:    Optional[str] = Field(default=None, max_length=2000)
    cover_media_id: Optional[int] = None


class MediaIdsRequest(BaseModel):
    media_ids: list[int]


# ── Helpers ───────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, project_id: int, user_id) -> Project:
    project = (await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


async def _serialize(db: AsyncSession, project: Project) -> dict:
    photos_count = (await db.execute(
        select(func.count()).select_from(MediaFile).where(MediaFile.project_id == project.id)
    )).scalar_one()

    stories_count = (await db.execute(
        select(func.count()).select_from(Story).where(Story.project_id == project.id)
    )).scalar_one()

    videos_count = (await db.execute(
        select(func.count()).select_from(VideoOutput).where(VideoOutput.project_id == project.id)
    )).scalar_one()

    return {
        "id":             project.id,
        "name":           project.name,
        "description":    project.description,
        "cover_media_id": project.cover_media_id,
        "created_at":     str(project.created_at),
        "updated_at":     str(project.updated_at),
        "photos_count":   photos_count,
        "stories_count":  stories_count,
        "videos_count":   videos_count,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────

@router.get("")
async def list_projects(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Lista os projetos do utilizador, mais recentes primeiro."""
    result = await db.execute(
        select(Project)
        .where(Project.user_id == user.id)
        .order_by(Project.updated_at.desc())
    )
    projects = result.scalars().all()
    return [await _serialize(db, p) for p in projects]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    project = Project(user_id=user.id, name=payload.name.strip(), description=payload.description)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    log.info("project_created", project_id=project.id, name=project.name)
    return await _serialize(db, project)


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    project = await _get_or_404(db, project_id, user.id)
    return await _serialize(db, project)


@router.patch("/{project_id}")
async def update_project(
    project_id: int,
    payload:    ProjectUpdate,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    project = await _get_or_404(db, project_id, user.id)

    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description
    if payload.cover_media_id is not None:
        # The cover must be one of THIS project's (isolated) photos.
        is_member = (await db.execute(
            select(MediaFile.id).where(
                MediaFile.id         == payload.cover_media_id,
                MediaFile.project_id == project_id,
                MediaFile.user_id    == user.id,
            )
        )).scalar_one_or_none()
        if not is_member:
            raise HTTPException(status_code=400, detail="A capa tem de ser uma foto adicionada ao projeto.")
        project.cover_media_id = payload.cover_media_id

    project.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(project)
    log.info("project_updated", project_id=project_id)
    return await _serialize(db, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    project = await _get_or_404(db, project_id, user.id)
    await db.delete(project)
    await db.commit()
    log.info("project_deleted", project_id=project_id)


# ── Photo membership ──────────────────────────────────────────────────────

@router.get("/{project_id}/media")
async def list_project_media(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    await _get_or_404(db, project_id, user.id)
    # Isolated: a project's photos are the media stamped with its project_id
    # (uploaded straight into the project), never the global Library.
    result = await db.execute(
        select(MediaFile)
        .where(MediaFile.project_id == project_id, MediaFile.user_id == user.id)
        .order_by(MediaFile.date_taken.desc().nullslast(), MediaFile.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{project_id}/media", status_code=status.HTTP_201_CREATED)
async def add_media_to_project(
    project_id: int,
    payload:    MediaIdsRequest,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    """Adiciona fotos ao projeto. Idempotente — duplicados são ignorados.

    Só permite associar fotos que pertencem ao utilizador — assim um user
    não consegue ligar (intencional ou acidentalmente) uma foto de outro.
    """
    await _get_or_404(db, project_id, user.id)
    if not payload.media_ids:
        return {"added": 0}

    existing = (await db.execute(
        select(ProjectMedia.media_id).where(
            ProjectMedia.project_id == project_id,
            ProjectMedia.media_id.in_(payload.media_ids),
        )
    )).scalars().all()
    already = set(existing)

    # Só conta como "valid" as fotos cujo owner é o caller.
    valid_ids = (await db.execute(
        select(MediaFile.id).where(
            MediaFile.id.in_(payload.media_ids),
            MediaFile.user_id == user.id,
        )
    )).scalars().all()
    valid = set(valid_ids)

    added = 0
    for mid in payload.media_ids:
        if mid in already or mid not in valid:
            continue
        db.add(ProjectMedia(project_id=project_id, media_id=mid))
        added += 1

    if added:
        project = (await db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user.id)
        )).scalar_one_or_none()
        if project is not None:
            project.updated_at = datetime.now(UTC)

    await db.commit()
    log.info("project_media_added", project_id=project_id, added=added)
    return {"added": added}


@router.delete("/{project_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_media_from_project(
    project_id: int,
    media_id:   int,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    project = await _get_or_404(db, project_id, user.id)
    # A project photo is project-only, so "remove from project" deletes it
    # (it isn't kept in the Library). The Storage object is best-effort cleaned.
    media = (await db.execute(
        select(MediaFile).where(
            MediaFile.id == media_id,
            MediaFile.user_id == user.id,
            MediaFile.project_id == project_id,
        )
    )).scalar_one_or_none()
    if media is not None:
        if media.file_path:
            try:
                await delete_object(media.file_path)
            except Exception as exc:                       # never fail the removal
                log.warning("project_media_storage_delete_swallowed", key=media.file_path, error=str(exc))
        await db.delete(media)
    if project.cover_media_id == media_id:
        project.cover_media_id = None
    await db.commit()


# ── Stories / videos do projeto ───────────────────────────────────────────

@router.get("/{project_id}/stories")
async def list_project_stories(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    await _get_or_404(db, project_id, user.id)
    result = await db.execute(
        select(Story)
        .where(Story.project_id == project_id, Story.user_id == user.id)
        .order_by(Story.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}/videos")
async def list_project_videos(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    user:       User         = Depends(get_current_user),
):
    await _get_or_404(db, project_id, user.id)
    result = await db.execute(
        select(VideoOutput)
        .where(VideoOutput.project_id == project_id, VideoOutput.user_id == user.id)
        .order_by(VideoOutput.created_at.desc())
    )
    # Same serialiser as the global listing → identical shape (size_mb,
    # download_url, poster_media_id) so the shared VideoCard works in both.
    from backend.api.routes.multimedia import serialize_videos
    return await serialize_videos(db, result.scalars().all(), user.id)
