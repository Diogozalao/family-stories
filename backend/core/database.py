"""Async SQLAlchemy engine and session factory — Supabase Postgres edition.

The schema lives in Supabase (created via ``backend/sql/0001_initial.sql``)
so the application never runs ``create_all``: it simply connects and
trusts that the migration has already happened. This keeps schema
ownership in one place — the SQL file — which is what we want.
"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings

log = structlog.get_logger()


def _to_async_url(url: str) -> str:
    """Force the asyncpg driver onto a plain ``postgresql://`` URL.

    Supabase hands users the URI with the bare ``postgresql`` scheme,
    which SQLAlchemy maps to the sync ``psycopg2`` driver. We're async,
    so rewrite the scheme upfront.
    """
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


_DATABASE_URL = _to_async_url(settings.SUPABASE_DB_URL or settings.DATABASE_URL)

# Supabase's transaction pooler (port 6543) rebinds each transaction to a
# random backend connection, which breaks asyncpg's named prepared
# statements. The two-part workaround is the standard recipe:
#   1. Disable asyncpg's statement cache so it never reuses statements
#      across transactions.
#   2. Generate unique server-side prepared-statement names so the pooler
#      never sees a collision either.
# See https://github.com/sqlalchemy/sqlalchemy/discussions/9038
engine = create_async_engine(
    _DATABASE_URL,
    echo          = False,
    pool_pre_ping = True,
    connect_args  = {
        "statement_cache_size":         0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_           = AsyncSession,
    expire_on_commit = False,
)


async def init_db() -> None:
    """Verify the connection at startup.

    Schema management is handled by the SQL migration in
    ``backend/sql/0001_initial.sql``, so this is purely a health check —
    if the connection fails, we want to know during startup rather than
    on the first request.
    """
    # Side-effect imports so the ORM mappers register on Base.metadata.
    # Useful for SQLAlchemy reflection / debugging tooling even though we
    # no longer call ``create_all``.
    from backend.models.media     import MediaFile        # noqa: F401
    from backend.models.narrative import Story            # noqa: F401
    from backend.models.project   import Project, ProjectMedia  # noqa: F401
    from backend.models.task      import TaskRecord       # noqa: F401
    from backend.models.timeline  import Person, TimelineEvent  # noqa: F401
    from backend.models.video     import VideoOutput      # noqa: F401

    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("database_connected", host=engine.url.host)


async def get_db():
    """FastAPI dependency yielding an ``AsyncSession`` per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
