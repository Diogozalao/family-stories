"""Application settings loaded from environment + .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App metadata.
    APP_NAME:    str = "Family Stories AI"
    APP_VERSION: str = "0.2.0"
    DEBUG:       bool = True

    # Filesystem layout — everything lives under the project root.
    BASE_DIR:      Path = Path(__file__).parent.parent.parent
    DATA_DIR:      Path = BASE_DIR / "data"
    RAW_DIR:       Path = DATA_DIR / "raw"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    VIDEOS_DIR:    Path = PROCESSED_DIR / "videos"
    AUDIO_DIR:     Path = PROCESSED_DIR / "audio"
    LOGS_DIR:      Path = BASE_DIR / "logs"

    # Persistence.
    DATABASE_URL: str = "sqlite+aiosqlite:///./family_stories.db"

    # Authentication / crypto.
    SECRET_KEY:                  str = "dev-secret-key-change-in-production"
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 days.

    # Redis / Celery broker URL (used by async job queue).
    REDIS_URL: str = "redis://localhost:6379/0"

    # External AI services.
    GEMINI_API_KEY:  str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL:    str = "llama3.1"

    # Upload size limits (in megabytes).
    MAX_PHOTO_SIZE_MB:  int = 25
    MAX_GEDCOM_SIZE_MB: int = 50

    # Rate limits applied by slowapi middleware (per client IP).
    RATE_LIMIT_DEFAULT:  str = "100/minute"
    RATE_LIMIT_UPLOAD:   str = "20/minute"
    RATE_LIMIT_GENERATE: str = "5/minute"

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
