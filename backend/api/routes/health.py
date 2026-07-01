"""Deep health checks for infrastructure dependencies.

The shallow ``/health`` endpoint (in ``main.py``) always returns 200 —
it only proves the HTTP server is up. This module exposes ``/healthz``
which probes each dependency the pipeline relies on and reports their
individual status. Useful for monitoring tools, for the thesis demo and
for debugging ("why is the narrative endpoint failing?").
"""

import shutil

import httpx
import structlog
from fastapi import APIRouter
from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import engine

router = APIRouter(tags=["health"])
log    = structlog.get_logger()

PROBE_TIMEOUT_SECONDS = 2.0


async def _check_database() -> dict:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


async def _check_ollama() -> dict:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        response.raise_for_status()
        models = [m.get("name") for m in response.json().get("models", [])]
        has_model = any(settings.OLLAMA_MODEL in (m or "") for m in models)
        return {
            "status": "ok" if has_model else "degraded",
            "models": models[:10],
            "expected_model": settings.OLLAMA_MODEL,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_gemini() -> dict:
    # Do not burn quota on a real API call — just verify the key is present.
    if not settings.GEMINI_API_KEY:
        return {"status": "disabled", "detail": "GEMINI_API_KEY not configured"}
    return {"status": "ok", "configured": True}


def _check_groq() -> dict:
    # Primary cloud TEXT backend (narratives). Key-presence check only — a real
    # call would spend the free quota.
    if not settings.GROQ_API_KEY:
        return {"status": "disabled", "detail": "GROQ_API_KEY not configured"}
    return {"status": "ok", "configured": True, "model": settings.GROQ_MODEL}


def _check_redis() -> dict:
    # Redis backs the OPTIONAL Celery task queue. The app degrades gracefully
    # to the in-process executor without it, so a missing/disabled Redis is
    # "disabled" (like the other optional backends), never a fatal error —
    # otherwise the aggregate health is falsely reported as "error".
    url = settings.REDIS_URL or ""
    if not url or "disabled" in url or "invalid" in url:
        return {"status": "disabled",
                "detail": "Redis not configured (in-process executor in use)"}
    try:
        import redis
        client = redis.Redis.from_url(url, socket_connect_timeout=PROBE_TIMEOUT_SECONDS)
        return {"status": "ok" if client.ping() else "warning"}
    except Exception as exc:
        # Optional dependency — an unreachable Redis degrades, it doesn't fail.
        return {"status": "warning", "detail": str(exc)}


def _check_chroma() -> dict:
    try:
        from backend.modules.m3_narrative.rag_system import RAGSystem
        rag = RAGSystem()
        return {"status": "ok", "total_facts": rag.total_facts}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_disk() -> dict:
    try:
        usage = shutil.disk_usage(settings.DATA_DIR)
        free_gb  = round(usage.free  / 1024**3, 2)
        total_gb = round(usage.total / 1024**3, 2)
        percent_used = round((usage.total - usage.free) / usage.total * 100, 1)
        return {
            "status":       "ok" if free_gb > 1.0 else "warning",
            "free_gb":      free_gb,
            "total_gb":     total_gb,
            "percent_used": percent_used,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/healthz")
async def deep_health() -> dict:
    """Run every dependency probe and report an aggregate status."""
    checks = {
        "database": await _check_database(),
        "ollama":   await _check_ollama(),
        "groq":     _check_groq(),
        "gemini":   _check_gemini(),
        "redis":    _check_redis(),
        "chroma":   _check_chroma(),
        "disk":     _check_disk(),
    }

    failures = [name for name, value in checks.items() if value.get("status") == "error"]
    warnings = [name for name, value in checks.items()
                if value.get("status") in ("warning", "degraded")]

    if failures:
        overall = "error"
    elif warnings:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status":   overall,
        "failures": failures,
        "warnings": warnings,
        "checks":   checks,
    }
