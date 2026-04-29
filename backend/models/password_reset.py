"""Persisted single-use tokens for the password-reset flow.

Two security choices worth highlighting:

* the **plaintext** token never lives in the database — only a SHA-256
  digest. Even with full read access to the SQLite file an attacker
  cannot replay an outstanding link.
* tokens are single-use. ``used_at`` is set on first redemption,
  preventing replay even before the TTL expires.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from backend.models.media import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # sha256 hex
    expires_at = Column(DateTime, nullable=False)
    used_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
