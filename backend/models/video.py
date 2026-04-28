"""Persistence model for generated documentary videos."""

import enum
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text

from backend.models.media import Base


class VideoStatus(str, enum.Enum):
    """Lifecycle state of a single video rendering job."""

    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class VideoOutput(Base):
    """One row per generated (or attempted) documentary video."""

    __tablename__ = "video_outputs"

    id            = Column(Integer, primary_key=True, index=True)
    story_id      = Column(Integer, ForeignKey("stories.id"), nullable=False)
    filename      = Column(String(255), nullable=True)
    file_path     = Column(String(500), nullable=True)
    file_size_mb  = Column(Float, nullable=True)
    photos_used   = Column(Integer, nullable=True)
    status        = Column(Enum(VideoStatus), default=VideoStatus.PROCESSING)
    error_message = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(UTC))
