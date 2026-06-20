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

    id           = Column(BigInteger, primary_key=True, index=True)
    user_id      = Column(UUID(as_uuid=True), nullable=False, index=True)
    name         = Column(String(255), nullable=False)
    sex          = Column(String(1), nullable=True)   # 'M' | 'F' | None
    birth_date   = Column(DateTime(timezone=True), nullable=True)
    death_date   = Column(DateTime(timezone=True), nullable=True)
    birth_place  = Column(String(255), nullable=True)
    notes        = Column(Text, nullable=True)
    gedcom_id    = Column(String(100), nullable=True)
    # Free-form label set at GEDCOM import time ("Dinis", "Nogueira", …)
    # so the Family page can group/filter trees coming from different
    # imports without forcing them into the same soup.
    family_label = Column(String(120), nullable=True)
    # Optional "profile photo" — the id of a MediaFile the user picked to
    # represent this person (a face for the tree, and a stronger anchor when
    # M3 weaves the person into a story). No FK constraint on purpose: the
    # column is a soft pointer, so deleting the photo just leaves it dangling
    # (the UI/serializer treats a missing media id as "no avatar").
    photo_media_id = Column(BigInteger, nullable=True)
    # Hand-arranged position in the interactive tree (NULL = auto-layout).
    tree_x       = Column(Float, nullable=True)
    tree_y       = Column(Float, nullable=True)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Relationship(Base):
    """A kinship edge between two persons, owned by ``user_id``.

    ``kind`` is one of ``pai`` / ``mãe`` (from_person is the parent of
    to_person) or ``cônjuge`` (spouses, stored once). Replaces the old
    on-disk JSON graph as the source of truth for relations.
    """
    __tablename__ = "relationships"

    id             = Column(BigInteger, primary_key=True, index=True)
    user_id        = Column(UUID(as_uuid=True), nullable=False, index=True)
    from_person_id = Column(BigInteger, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    to_person_id   = Column(BigInteger, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False, index=True)
    kind           = Column(String(16), nullable=False)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id              = Column(BigInteger, primary_key=True, index=True)
    user_id         = Column(UUID(as_uuid=True), nullable=False, index=True)

    event_date      = Column(DateTime(timezone=True), nullable=True)
    date_confidence = Column(Enum(ConfidenceLevel, name="confidence_level", create_type=False, values_callable=lambda x: [e.value for e in x]),
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
