from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Enum
from backend.models.media import Base
from datetime import datetime
import enum

class StoryStatus(str, enum.Enum):
    DRAFT     = "draft"
    COMPLETED = "completed"
    FAILED    = "failed"

class Story(Base):
    __tablename__ = "stories"

    id            = Column(Integer, primary_key=True, index=True)
    title         = Column(String(255), nullable=False)
    event_type    = Column(String(50), default="default")
    narrative     = Column(Text, nullable=False)
    template_used = Column(String(100), nullable=True)
    llm_backend   = Column(String(50), nullable=True)  # ollama ou gemini
    facts_used    = Column(Integer, default=0)
    prompt_used   = Column(Text, nullable=True)
    status        = Column(Enum(StoryStatus), default=StoryStatus.DRAFT)
    person_ids    = Column(JSON, default=list)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
