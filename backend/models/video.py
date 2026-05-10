"""Generated documentary videos.

Backed by the Postgres table ``video_outputs`` from
``backend/sql/0001_initial.sql``.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from backend.models.media import Base


class VideoStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class VideoOutput(Base):
    __tablename__ = "video_outputs"

    id           = Column(BigInteger, primary_key=True, index=True)
    user_id      = Column(UUID(as_uuid=True), nullable=False, index=True)
    story_id     = Column(BigInteger, ForeignKey("stories.id",  ondelete="CASCADE"), nullable=False)
    project_id   = Column(BigInteger, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)

    filename     = Column(String(255), nullable=True)
    file_path    = Column(String(500), nullable=True)        # Supabase Storage object key
    file_size_mb = Column(Float, nullable=True)
    photos_used  = Column(Integer, nullable=True)
    status       = Column(Enum(VideoStatus, name="video_status", create_type=False),
                          default=VideoStatus.PROCESSING)
    error_message = Column(Text, nullable=True)

    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
