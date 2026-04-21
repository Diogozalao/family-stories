"""Async SQLAlchemy engine, session factory and schema bootstrap."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.models.media import Base

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
    from backend.models.media import MediaFile                    # noqa: F401
    from backend.models.narrative import Story                    # noqa: F401
    from backend.models.timeline import Person, TimelineEvent     # noqa: F401
    from backend.models.user import User                          # noqa: F401
    from backend.models.video import VideoOutput                  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency yielding an ``AsyncSession`` per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
