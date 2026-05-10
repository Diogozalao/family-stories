"""Persons (GEDCOM-imported) and timeline events.

Backed by the Postgres tables created in ``backend/sql/0001_initial.sql``.
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.models.media import Base


class ConfidenceLevel(str, enum.Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class Person(Base):
    __tablename__ = "persons"

    id          = Column(BigInteger, primary_key=True, index=True)
    user_id     = Column(UUID(as_uuid=True), nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    birth_date  = Column(DateTime(timezone=True), nullable=True)
    death_date  = Column(DateTime(timezone=True), nullable=True)
    birth_place = Column(String(255), nullable=True)
    notes       = Column(Text, nullable=True)
    gedcom_id   = Column(String(100), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id              = Column(BigInteger, primary_key=True, index=True)
    user_id         = Column(UUID(as_uuid=True), nullable=False, index=True)

    event_date      = Column(DateTime(timezone=True), nullable=True)
    date_confidence = Column(Enum(ConfidenceLevel, name="confidence_level", create_type=False),
                             default=ConfidenceLevel.LOW)
    date_label      = Column(String(100), nullable=True)

    event_type      = Column(String(50), nullable=True)
    title           = Column(String(255), nullable=True)
    description     = Column(Text, nullable=True)
    location        = Column(String(255), nullable=True)
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)

    media_file_id   = Column(BigInteger, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True)
    person_ids      = Column(JSONB, default=list)
    sort_order      = Column(Integer, default=0)

    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
