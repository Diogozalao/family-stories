"""Background task tracking.

Each long-running operation (narrative generation, video assembly) is
dispatched to a Celery worker. ``TaskRecord`` keeps a human-friendly
projection of the task's state in the main SQLite database so clients
can poll a single endpoint to know what is happening with their job.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text

from backend.models.media import Base


class TaskKind(str, enum.Enum):
    """Which pipeline the task belongs to."""

    NARRATIVE = "narrative"
    VIDEO     = "video"
    INGEST    = "ingest"


class TaskState(str, enum.Enum):
    """Lifecycle states for background jobs."""

    PENDING = "pending"   # Enqueued, worker hasn't picked it up.
    RUNNING = "running"   # Worker started.
    DONE    = "done"
    FAILED  = "failed"


class TaskRecord(Base):
    __tablename__ = "task_records"

    id         = Column(Integer, primary_key=True, index=True)
    celery_id  = Column(String(64),  unique=True, index=True, nullable=True)
    kind       = Column(Enum(TaskKind),  nullable=False)
    state      = Column(Enum(TaskState), default=TaskState.PENDING, nullable=False)

    # Cross-references to domain records. Only one will be populated per task,
    # depending on ``kind``. Kept nullable to avoid cascading migrations later.
    story_id   = Column(Integer, ForeignKey("stories.id"),       nullable=True)
    video_id   = Column(Integer, ForeignKey("video_outputs.id"), nullable=True)

    # Free-form payload echoed back to the client (e.g. the request body).
    payload    = Column(JSON, nullable=True)
    result     = Column(JSON, nullable=True)
    error      = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
