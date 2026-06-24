"""ORM model for ingested media — photos, videos, documents, GEDCOM.

Backed by the Postgres table created in ``backend/sql/0001_initial.sql``.
Every row is owned by a Supabase ``auth.users`` UUID (``user_id``) and
isolated by Row Level Security at the database level.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class MediaType(str, enum.Enum):
    PHOTO    = "photo"
    VIDEO    = "video"
    DOCUMENT = "document"
    GEDCOM   = "gedcom"


class ProcessingStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class MediaFile(Base):
    __tablename__ = "media_files"

    id      = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # NULL = global Library; set = belongs to (and only shows inside) a project.
    # FK enforced in SQL (0010_project_isolation.sql); plain column here to
    # avoid cross-model metadata resolution.
    project_id = Column(BigInteger, nullable=True, index=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename   = Column(String(255), nullable=False)
    file_path         = Column(String(500), nullable=False)   # Supabase Storage object key
    file_size         = Column(Integer)
    mime_type         = Column(String(100))
    media_type        = Column(Enum(MediaType, name="media_type", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False)

    date_taken    = Column(DateTime(timezone=True), nullable=True)
    latitude      = Column(Float, nullable=True)
    longitude     = Column(Float, nullable=True)
    location_name = Column(String(255), nullable=True)
    camera_make   = Column(String(100), nullable=True)
    camera_model  = Column(String(100), nullable=True)

    ai_description    = Column(Text, nullable=True)
    ai_people_count   = Column(Integer, nullable=True)
    ai_setting        = Column(String(255), nullable=True)
    ai_emotion        = Column(String(100), nullable=True)
    ai_tags           = Column(JSONB, nullable=True)
    ai_narrative_hint = Column(Text, nullable=True)

    ocr_text = Column(Text, nullable=True)

    # Ids of the persons (from the family tree) that appear in this photo —
    # the link that lets M3/M4 connect faces to names in the story.
    person_ids = Column(JSONB, default=list)

    is_safe      = Column(Boolean, default=True)
    checksum_md5 = Column(String(32), nullable=True)
    raw_exif     = Column(JSONB, nullable=True)

    status        = Column(Enum(ProcessingStatus, name="processing_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
                           default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
