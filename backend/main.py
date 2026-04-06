from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.database import init_db
from backend.api.routes.upload import router as upload_router
from backend.api.routes.timeline import router as timeline_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Geração Automática de Histórias Familiares com IA Generativa",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(timeline_router)

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "modules": {
            "M1": "Ingestão Multimodal ✓",
            "M2": "Organização Temporal ✓",
            "M3": "Geração Narrativa (pendente)",
            "M4": "Geração Multimédia (pendente)",
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
