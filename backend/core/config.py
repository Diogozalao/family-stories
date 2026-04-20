from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Family Stories AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    VIDEOS_DIR: Path = PROCESSED_DIR / "videos"
    AUDIO_DIR: Path = PROCESSED_DIR / "audio"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./family_stories.db"
    
    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AI - Gemini (gratuito)
    GEMINI_API_KEY: str = ""
    
    # AI - Ollama (local, gratuito)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    
    class Config:
        env_file = ".env"

settings = Settings()
