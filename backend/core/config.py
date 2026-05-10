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
    GEMINI_MODEL:    str = "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL:    str = "llama3.2:3b"
    NARRATIVE_MAX_TOKENS: int = 3500

    # Upload size limits (in megabytes).
    MAX_PHOTO_SIZE_MB:  int = 25
    MAX_GEDCOM_SIZE_MB: int = 50

    # Rate limits applied by slowapi middleware (per client IP).
    RATE_LIMIT_DEFAULT:  str = "100/minute"
    RATE_LIMIT_UPLOAD:   str = "20/minute"
    RATE_LIMIT_GENERATE: str = "5/minute"

    # Public URL the frontend is served from. Used to build absolute
    # links inside outgoing emails (password reset, etc.).
    FRONTEND_URL: str = "http://localhost:5173"

    # ── SMTP (opcional) ──────────────────────────────────────────────
    # Quando ``SMTP_ENABLED=False`` (default), o sistema mantém-se
    # totalmente local: pedidos de reset de palavra-passe geram um
    # token e o link é escrito no log do backend (útil para demo /
    # tese sem servidor de email). Quando ligado, o link é enviado
    # por email para o utilizador.
    SMTP_ENABLED:  bool = False
    SMTP_HOST:     str  = "smtp.gmail.com"
    SMTP_PORT:     int  = 587
    SMTP_USERNAME: str  = ""
    SMTP_PASSWORD: str  = ""
    SMTP_FROM:     str  = "Living Memory <noreply@livingmemory.local>"
    SMTP_USE_TLS:  bool = True

    # Token de reset de password — vida útil em minutos.
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 60

    # ── Supabase ─────────────────────────────────────────────────────
    # Auth (signup/login/reset) e BD passam a ser geridos pelo Supabase.
    # ``SUPABASE_URL`` é público; ``SERVICE_ROLE_KEY`` é privado e só
    # deve ser usado pelo backend para operações administrativas.
    SUPABASE_URL:              str = ""
    SUPABASE_ANON_KEY:         str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL:           str = ""
    SUPABASE_DB_DIRECT_URL:    str = ""

    # JWKS endpoint usado para validar tokens emitidos pelo Supabase Auth.
    # Construído automaticamente a partir do SUPABASE_URL.
    @property
    def SUPABASE_JWKS_URL(self) -> str:
        return f"{self.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"
        extra             = "ignore"   # ignora NEXT_PUBLIC_* e outras vars do frontend


settings = Settings()
