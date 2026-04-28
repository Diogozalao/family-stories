
"""Authentication user model.

The application is single-user in spirit (it holds one family's archive)
but the schema is deliberately shaped like a regular multi-user table so
the frontend can later support invited collaborators without a
migration.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from backend.models.media import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(64),  unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_owner        = Column(Boolean, default=False)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=lambda: datetime.now(UTC))
