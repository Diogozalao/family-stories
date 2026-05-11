"""Background task tracking.

Backed by the Postgres table ``task_records`` from
``backend/sql/0001_initial.sql``.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.models.media import Base


class TaskKind(str, enum.Enum):
    NARRATIVE = "narrative"
    VIDEO     = "video"
    INGEST    = "ingest"


class TaskState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


class TaskRecord(Base):
    __tablename__ = "task_records"

    id        = Column(BigInteger, primary_key=True, index=True)
    user_id   = Column(UUID(as_uuid=True), nullable=False, index=True)
    celery_id = Column(String(64), unique=True, index=True, nullable=True)
    kind      = Column(Enum(TaskKind,  name="task_kind",  create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    state     = Column(Enum(TaskState, name="task_state", create_type=False, values_callable=lambda x: [e.value for e in x]),
                       default=TaskState.PENDING, nullable=False)

    story_id  = Column(BigInteger, ForeignKey("stories.id",       ondelete="CASCADE"), nullable=True)
    video_id  = Column(BigInteger, ForeignKey("video_outputs.id", ondelete="CASCADE"), nullable=True)

    payload   = Column(JSONB, nullable=True)
    result    = Column(JSONB, nullable=True)
    error     = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC),
                        onupdate=lambda: datetime.now(UTC))
