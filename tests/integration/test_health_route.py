"""Smoke test for the shallow and deep health endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_shallow_health_always_ok(db_session):
    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_deep_health_returns_structured_report(db_session):
    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "degraded", "error")
        assert set(body["checks"].keys()) == {
            "database", "ollama", "gemini", "redis", "chroma", "disk"
        }
        assert body["checks"]["database"]["status"] == "ok"
