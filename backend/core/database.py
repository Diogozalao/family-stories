"""Async SQLAlchemy engine, session factory and schema bootstrap."""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.models.media import Base

log = structlog.get_logger()

# Turn off engine echo when DEBUG is true to avoid flooding the console —
# route-level structured logs already show what we need.
engine = create_async_engine(str(settings.DATABASE_URL), echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_             = AsyncSession,
    expire_on_commit   = False,
)


async def init_db() -> None:
    """Create every ORM table declared on the shared Base metadata.

    Models must be imported before ``create_all`` runs — otherwise their
    tables are absent from ``Base.metadata`` and the CREATE statements
    are silently skipped.
    """
    # Side-effect imports — do NOT remove even though the names look unused.
    from backend.models.media import MediaFile                          # noqa: F401
    from backend.models.narrative import Story                          # noqa: F401
    from backend.models.password_reset import PasswordResetToken        # noqa: F401
    from backend.models.project import Project, ProjectMedia            # noqa: F401
    from backend.models.task import TaskRecord                          # noqa: F401
    from backend.models.timeline import Person, TimelineEvent           # noqa: F401
    from backend.models.user import User                                # noqa: F401
    from backend.models.video import VideoOutput                        # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migrations for columns added after the initial release.
        await _ensure_column(conn, "stories",       "project_id", "INTEGER")
        await _ensure_column(conn, "video_outputs", "project_id", "INTEGER")


async def _ensure_column(conn, table: str, column: str, sql_type: str) -> None:
    """Add ``column`` to ``table`` if it is not already present.

    SQLite does not enforce schema migrations and ``create_all`` does not
    ``ALTER`` existing tables. This helper bridges the gap for additive
    changes — it is *not* a substitute for Alembic, but enough for the
    incremental columns we add as the product grows.
    """
    rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
    existing = {r[1] for r in rows}
    if column in existing:
        return
    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
    log.info("schema_column_added", table=table, column=column)


async def get_db():
    """FastAPI dependency yielding an ``AsyncSession`` per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
