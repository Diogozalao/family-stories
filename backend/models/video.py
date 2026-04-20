from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Enum, ForeignKey
from backend.models.media import Base
from datetime import datetime
import enum


class VideoStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class VideoOutput(Base):
    __tablename__ = "video_outputs"

    id            = Column(Integer, primary_key=True, index=True)
    story_id      = Column(Integer, ForeignKey("stories.id"), nullable=False)
    filename      = Column(String(255), nullable=True)
    file_path     = Column(String(500), nullable=True)
    file_size_mb  = Column(Float, nullable=True)
    photos_used   = Column(Integer, nullable=True)
    status        = Column(Enum(VideoStatus), default=VideoStatus.PROCESSING)
    error_message = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
