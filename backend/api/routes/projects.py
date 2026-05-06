"""Projetos / coleções — espaços de trabalho que agrupam fotos, histórias e vídeos.

Um ``Project`` é uma vista filtrada e curada sobre a Biblioteca global.
A intenção é separar contextos (ex.: *Casamento dos avós*, *Viagem ao
Algarve 1985*) sem duplicar fotografias no disco.
"""

from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.media import MediaFile
from backend.models.narrative import Story
from backend.models.project import Project, ProjectMedia
from backend.models.user import User
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

async def _get_or_404(db: AsyncSession, project_id: int) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


async def _serialize(db: AsyncSession, project: Project) -> dict:
    photos_count = (await db.execute(
        select(func.count()).select_from(ProjectMedia).where(ProjectMedia.project_id == project.id)
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
    db:    AsyncSession = Depends(get_db),
    _user: User         = Depends(get_current_user),
):
    """Lista todos os projetos, mais recentes primeiro."""
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    projects = result.scalars().all()
    return [await _serialize(db, p) for p in projects]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db:      AsyncSession = Depends(get_db),
    _user:   User         = Depends(get_current_user),
):
    project = Project(name=payload.name.strip(), description=payload.description)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    log.info("project_created", project_id=project.id, name=project.name)
    return await _serialize(db, project)


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    _user:      User         = Depends(get_current_user),
):
    project = await _get_or_404(db, project_id)
    return await _serialize(db, project)


@router.patch("/{project_id}")
async def update_project(
    project_id: int,
    payload:    ProjectUpdate,
    db:         AsyncSession = Depends(get_db),
    _user:      User         = Depends(get_current_user),
):
    project = await _get_or_404(db, project_id)

    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description
    if payload.cover_media_id is not None:
        # Validar que a foto existe e pertence ao projeto.
        is_member = (await db.execute(
            select(ProjectMedia.id).where(
                ProjectMedia.project_id == project_id,
                ProjectMedia.media_id   == payload.cover_media_id,
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
    _user:      User         = Depends(get_current_user),
):
    """Elimina o projeto.

    As fotografias na ``Biblioteca`` permanecem intactas — só
    desaparecem as associações em ``project_media`` (CASCADE).
    Histórias e vídeos perdem a ligação (``ON DELETE SET NULL``)
    mas ficam acessíveis nas listagens globais.
    """
    project = await _get_or_404(db, project_id)
    await db.delete(project)
    await db.commit()
    log.info("project_deleted", project_id=project_id)


# ── Photo membership ──────────────────────────────────────────────────────

@router.get("/{project_id}/media")
async def list_project_media(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    _user:      User         = Depends(get_current_user),
):
    await _get_or_404(db, project_id)
    result = await db.execute(
        select(MediaFile)
        .join(ProjectMedia, ProjectMedia.media_id == MediaFile.id)
        .where(ProjectMedia.project_id == project_id)
        .order_by(MediaFile.date_taken.desc().nullslast(), MediaFile.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{project_id}/media", status_code=status.HTTP_201_CREATED)
async def add_media_to_project(
    project_id: int,
    payload:    MediaIdsRequest,
    db:         AsyncSession = Depends(get_db),
    _user:      User         = Depends(get_current_user),
):
    """Adiciona fotos ao projeto. Idempotente — duplicados são ignorados."""
    await _get_or_404(db, project_id)
    if not payload.media_ids:
        return {"added": 0}

    existing = (await db.execute(
        select(ProjectMedia.media_id).where(
            ProjectMedia.project_id == project_id,
            ProjectMedia.media_id.in_(payload.media_ids),
        )
    )).scalars().all()
    already = set(existing)

    valid_ids = (await db.execute(
        select(MediaFile.id).where(MediaFile.id.in_(payload.media_ids))
    )).scalars().all()
    valid = set(valid_ids)

    added = 0
    for mid in payload.media_ids:
        if mid in already or mid not in valid:
            continue
        db.add(ProjectMedia(project_id=project_id, media_id=mid))
        added += 1

    if added:
        # Atualizar updated_at do projeto para que se mova para o topo da lista.
        project = await db.get(Project, project_id)
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
    _user:      User         = Depends(get_current_user),
):
    """Remove a foto do projeto. A foto continua na Biblioteca."""
    await _get_or_404(db, project_id)
    await db.execute(
        delete(ProjectMedia).where(
            ProjectMedia.project_id == project_id,
            ProjectMedia.media_id   == media_id,
        )
    )
    # Se era capa, limpar.
    project = await db.get(Project, project_id)
    if project is not None and project.cover_media_id == media_id:
        project.cover_media_id = None
    await db.commit()


# ── Stories / videos do projeto ───────────────────────────────────────────

@router.get("/{project_id}/stories")
async def list_project_stories(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    _user:      User         = Depends(get_current_user),
):
    await _get_or_404(db, project_id)
    result = await db.execute(
        select(Story).where(Story.project_id == project_id).order_by(Story.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}/videos")
async def list_project_videos(
    project_id: int,
    db:         AsyncSession = Depends(get_db),
    _user:      User         = Depends(get_current_user),
):
    await _get_or_404(db, project_id)
    result = await db.execute(
        select(VideoOutput).where(VideoOutput.project_id == project_id).order_by(VideoOutput.created_at.desc())
    )
    return result.scalars().all()
