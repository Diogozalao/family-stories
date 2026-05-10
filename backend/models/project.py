"""Project workspaces (curated photo subsets + stories + videos).

Backed by the Postgres tables ``projects`` and ``project_media`` from
``backend/sql/0001_initial.sql``.
"""

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from backend.models.media import Base


class Project(Base):
    __tablename__ = "projects"

    id             = Column(BigInteger, primary_key=True, index=True)
    user_id        = Column(UUID(as_uuid=True), nullable=False, index=True)
    name           = Column(String(120), nullable=False)
    description    = Column(Text, nullable=True)
    cover_media_id = Column(BigInteger, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                            onupdate=lambda: datetime.now(UTC), nullable=False)


class ProjectMedia(Base):
    """Many-to-many junction Project ↔ MediaFile.

    Does NOT carry a ``user_id`` column — ownership is inferred from the
    referenced project (enforced both by application code and by the
    Supabase RLS policy that joins through ``projects``).
    """

    __tablename__ = "project_media"
    __table_args__ = (UniqueConstraint("project_id", "media_id", name="uq_project_media"),)

    id         = Column(BigInteger, primary_key=True, index=True)
    project_id = Column(BigInteger, ForeignKey("projects.id",    ondelete="CASCADE"), nullable=False, index=True)
    media_id   = Column(BigInteger, ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
