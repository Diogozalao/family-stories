"""Shared pytest fixtures.

Every test that touches the database uses a disposable SQLite file
inside a temp directory so tests never pollute the real
``family_stories.db`` next to the project root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Make the project root importable when pytest is invoked from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def _isolate_env(tmp_path_factory):
    """Point every filesystem-dependent setting at a temp workspace."""
    workspace = tmp_path_factory.mktemp("fs_ai_tests")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{workspace/'test.db'}"
    os.environ["SECRET_KEY"]   = "test-secret-key"
    os.environ["REDIS_URL"]    = "redis://localhost:6379/15"
    return workspace


@pytest_asyncio.fixture
async def db_session(_isolate_env):
    """Yield a fresh AsyncSession against a schema created on the fly."""
    # Import lazily so the env overrides above are in effect.
    from backend.core.database import AsyncSessionLocal, engine
    from backend.models.media import Base
    from backend.models import media, narrative, timeline, user, video  # noqa: F401
    from backend.models import task                                      # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        yield session
