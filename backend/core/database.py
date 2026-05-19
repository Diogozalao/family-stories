"""Async SQLAlchemy engine and session factory — Supabase Postgres edition.

The schema lives in Supabase (created via ``backend/sql/0001_initial.sql``)
so the application never runs ``create_all``: it simply connects and
trusts that the migration has already happened. This keeps schema
ownership in one place — the SQL file — which is what we want.

Pooler-mode autodetect: Supabase exposes two pooler ports on
``aws-0-<REGION>.pooler.supabase.com``:

  * ``5432`` — **session pooler**: sticky session per connection;
              prepared statements work normally. Fastest for FastAPI.
  * ``6543`` — **transaction pooler**: connection rebound per
              transaction; we must disable asyncpg's prepared-statement
              cache and give every statement a unique server-side name
              so pgbouncer doesn't collide them across backends.

We pick the right ``connect_args`` automatically by inspecting the
URL's port. That way switching pooler modes is a single ``.env`` edit
with no code change.
"""

import uuid
from urllib.parse import urlparse

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import settings

log = structlog.get_logger()


def _to_async_url(url: str) -> str:
    """Force the asyncpg driver onto a plain ``postgresql://`` URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


_DATABASE_URL = _to_async_url(settings.SUPABASE_DB_URL or settings.DATABASE_URL)


def _connect_args_for(url: str) -> dict:
    """Return asyncpg ``connect_args`` matched to the URL's pooler mode."""
    try:
        port = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1)).port
    except ValueError:
        port = None

    # Transaction pooler rewrites every transaction onto a fresh backend
    # connection. asyncpg's prepared-statement cache is keyed by server
    # process id, so reuse breaks immediately. Workaround = no client
    # cache + unique statement names per call.
    if port == 6543:
        log.info("db_mode_detected", mode="transaction_pooler", port=port)
        return {
            "statement_cache_size":          0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func":  lambda: f"__asyncpg_{uuid.uuid4().hex}__",
        }

    # Default — session pooler (5432) or direct connection. Normal
    # prepared statements are fine; no workaround needed.
    log.info("db_mode_detected", mode="session_or_direct", port=port)
    return {}


engine = create_async_engine(
    _DATABASE_URL,
    echo          = False,
    pool_pre_ping = True,
    pool_size     = 5,
    max_overflow  = 5,
    pool_recycle  = 1800,
    connect_args  = _connect_args_for(_DATABASE_URL),
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
    from backend.models.media     import MediaFile                # noqa: F401
    from backend.models.narrative import Story                    # noqa: F401
    from backend.models.project   import Project, ProjectMedia    # noqa: F401
    from backend.models.task      import TaskRecord               # noqa: F401
    from backend.models.timeline  import Person, TimelineEvent    # noqa: F401
    from backend.models.video     import VideoOutput              # noqa: F401

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
