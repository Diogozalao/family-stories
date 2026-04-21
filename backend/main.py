"""FastAPI entry point for Family Stories AI.

Wires together:
    * Structured logging (stdout + rotating file)
    * Schema creation on startup
    * Per-IP rate limiting (slowapi)
    * Route groups for auth, uploads, timeline, narrative, genealogy,
      multimedia, background tasks and deep health checks
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.api.routes.auth       import router as auth_router
from backend.api.routes.genealogy  import router as genealogy_router
from backend.api.routes.health     import router as health_router
from backend.api.routes.multimedia import router as multimedia_router
from backend.api.routes.narrative  import router as narrative_router
from backend.api.routes.tasks      import router as tasks_router
from backend.api.routes.timeline   import router as timeline_router
from backend.api.routes.upload     import router as upload_router
from backend.core.config           import settings
from backend.core.database         import init_db
from backend.core.logging          import configure_logging
from backend.core.rate_limit       import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup + shutdown hooks."""
    configure_logging()
    await init_db()
    yield


app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = "Automatic family-story generation with generative AI",
    lifespan    = lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(timeline_router)
app.include_router(narrative_router)
app.include_router(genealogy_router)
app.include_router(multimedia_router)
app.include_router(tasks_router)
app.include_router(health_router)


# ── Root & shallow health ─────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "online",
        "modules": {
            "M1": "Ingestão Multimodal ✓",
            "M2": "Organização Temporal ✓",
            "M3": "Geração Narrativa ✓",
            "M4": "Geração Multimédia ✓",
        },
        "endpoints": {
            "deep_health": "/healthz",
            "auth":        "/api/v1/auth",
            "tasks":       "/api/v1/tasks",
        },
    }


@app.get("/health")
async def health():
    """Shallow liveness probe — always returns 200 if the server is up."""
    return {"status": "healthy"}
