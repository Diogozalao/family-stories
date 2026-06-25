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
    # Toggle the Celery job queue. Set ``CELERY_ENABLED=False`` when
    # deploying to environments without a worker — every ``mode=background``
    # API call is then transparently downgraded to a synchronous run, so
    # the user still gets their narrative/video, just from the same HTTP
    # request instead of via a follow-up task poll.
    CELERY_ENABLED: bool = True

    # External AI services.
    GEMINI_API_KEY:  str = ""
    # Use a currently-available model. Gemini 1.5 is no longer served to API
    # keys created after ~April 2025, which silently broke narrative
    # generation (M1 already used 2.5-flash, which is why photo analysis kept
    # working while narratives failed). Override via env if needed.
    GEMINI_MODEL:    str = "gemini-2.5-flash"   # M1 vision (short prompts → fast)
    # M3 narrative text. 2.5-flash has "thinking" on by default, which for a
    # ~3500-token narrative often runs past Render's ~100 s proxy limit and the
    # request gets dropped. 2.0-flash has no thinking and writes in ~15-25 s.
    GEMINI_TEXT_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT:  int = 60          # seconds per LLM call before giving up
    # Hard wall-clock cap per background task. The in-process executor runs a
    # single worker, so a hung task would block the whole queue; this frees it.
    # A documentary render is the heaviest case, hence the generous default.
    TASK_MAX_SECONDS: int = 600
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL:    str = "llama3.2:3b"
    # Groq — rede de segurança SÓ para texto, usada apenas se o Gemini falhar.
    # API compatível com OpenAI, modelos abertos, free tier generoso → custo
    # zero. Sem chave configurada, o fallback fica inativo (Ollama→Gemini só).
    # Não cobre a visão do M1, que se mantém Gemini-only.
    GROQ_API_KEY: str = ""
    GROQ_MODEL:   str = "llama-3.3-70b-versatile"
    NARRATIVE_MAX_TOKENS: int = 3500

    # M4 video render frame size / fps. Lower these on a memory-constrained
    # host (Render free = 512MB runs out of memory at 720p): set
    # VIDEO_WIDTH=854, VIDEO_HEIGHT=480, VIDEO_FPS=20 via env. Local dev keeps
    # full 720p24 quality by default.
    VIDEO_WIDTH:  int = 1280
    VIDEO_HEIGHT: int = 720
    VIDEO_FPS:    int = 24

    # Force the video endpoint to render SYNCHRONOUSLY regardless of the mode
    # the client asks for. Set ``True`` in the cloud (Render): there is no
    # Celery worker there, so a "background" job would run on an in-process
    # thread that the free instance kills when it sleeps — leaving the video
    # stuck "processing" forever. Sync keeps the instance awake for the render
    # and fails visibly if it runs out of memory. Locally this stays ``False``
    # so the browser isn't blocked on a multi-minute 720p render.
    VIDEO_FORCE_SYNC: bool = False

    # Upload size limits (in megabytes).
    MAX_PHOTO_SIZE_MB:  int = 25
    MAX_GEDCOM_SIZE_MB: int = 100   # ample headroom for trees with thousands of persons

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
