# Production image for the Family Stories backend.
#
# Slim Python base + the system libraries our wheels (moviepy, magic,
# tesseract, pillow) need at runtime. Render uses this whenever
# ``dockerfilePath: ./Dockerfile`` is set in render.yaml — otherwise it
# would fall back to the buildpack, which doesn't install the apt
# packages and dies the first time M1 tries to ``import magic``.

FROM python:3.12-slim

# Avoid prompts, faster pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System packages our wheels link against. Keep this list tight — every
# extra MB delays Render's free-tier cold start.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg                \
        libmagic1             \
        tesseract-ocr         \
        tesseract-ocr-por     \
        libjpeg-dev           \
        zlib1g-dev            \
        ca-certificates       \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (cached layer when only source code changes).
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Application code.
COPY backend ./backend
COPY data    ./data

# Render injects ``$PORT`` at runtime — bind 0.0.0.0 so the platform
# router can reach us. Single worker is enough on free tier (512 MB).
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
