"""Generated narratives.

Backed by the Postgres table ``stories`` created in
``backend/sql/0001_initial.sql``.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.models.media import Base


class StoryStatus(str, enum.Enum):
    DRAFT     = "draft"
    COMPLETED = "completed"
    FAILED    = "failed"


class Story(Base):
    __tablename__ = "stories"

    id            = Column(BigInteger, primary_key=True, index=True)
    user_id       = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id    = Column(BigInteger, ForeignKey("projects.id", ondelete="SET NULL"),
                           nullable=True, index=True)

    title         = Column(String(255), nullable=False)
    event_type    = Column(String(50), default="default")
    narrative     = Column(Text, nullable=False)
    template_used = Column(String(100), nullable=True)
    llm_backend   = Column(String(50), nullable=True)
    facts_used    = Column(Integer, default=0)
    prompt_used   = Column(Text, nullable=True)
    status        = Column(Enum(StoryStatus, name="story_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
                           default=StoryStatus.DRAFT)
    person_ids    = Column(JSONB, default=list)

    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                           onupdate=lambda: datetime.now(UTC))
