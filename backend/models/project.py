"""Espaços de trabalho que agrupam fotografias, histórias e vídeos.

Um ``Project`` representa um caso de uso curado pelo utilizador
(ex.: "Casamento do Avô", "Verões em Sintra"). A `Biblioteca`
continua a ser o repositório global; o projeto é uma vista filtrada
sobre uma sub-parte das fotos, com as histórias/vídeos que foram
gerados especificamente para esse contexto.

Relações:

    Project ─┬─ ProjectMedia ─── MediaFile      (many-to-many)
             ├─ Story.project_id                 (one-to-many)
             └─ VideoOutput.project_id           (one-to-many)
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from backend.models.media import Base


class Project(Base):
    __tablename__ = "projects"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(120), nullable=False)
    description     = Column(Text, nullable=True)
    cover_media_id  = Column(Integer, ForeignKey("media_files.id"), nullable=True)
    created_at      = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at      = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ProjectMedia(Base):
    """Tabela de junção Project ↔ MediaFile."""

    __tablename__ = "project_media"
    __table_args__ = (UniqueConstraint("project_id", "media_id", name="uq_project_media"),)

    id         = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id   = Column(Integer, ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at   = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
