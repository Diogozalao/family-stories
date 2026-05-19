#!/usr/bin/env bash
# Living Memory — launcher único
# Arranca Redis, backend (FastAPI :8000), Celery worker, frontend (Vite :5173)
# e abre o browser na aplicação. Ctrl+C termina tudo.

set -e
cd "$(dirname "$0")"

ROOT="$(pwd)"
LOG_DIR="$ROOT/logs/launcher"
mkdir -p "$LOG_DIR"

B='\033[1m'; G='\033[32m'; Y='\033[33m'; R='\033[31m'; D='\033[2m'; N='\033[0m'
say()  { printf "${B}${G}▸${N} %s\n" "$*"; }
warn() { printf "${B}${Y}!${N} %s\n" "$*"; }
fail() { printf "${B}${R}✗${N} %s\n" "$*"; exit 1; }

PIDS=()
cleanup() {
  echo
  say "A terminar serviços…"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # mata também filhos órfãos nas portas conhecidas
  fuser -k 8000/tcp 2>/dev/null || true
  fuser -k 5173/tcp 2>/dev/null || true
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM EXIT

# 0. venv
[ -d "$ROOT/venv" ] || fail "venv não encontrado em $ROOT/venv — corre 'python -m venv venv' primeiro"
# shellcheck disable=SC1091
source "$ROOT/venv/bin/activate"

# 1. Redis
if redis-cli ping >/dev/null 2>&1; then
  say "Redis  ✓"
else
  warn "Redis não está a correr — a iniciar (pode pedir password de sudo)…"
  sudo service redis-server start || fail "Falha ao iniciar Redis"
  sleep 1
  redis-cli ping >/dev/null 2>&1 || fail "Redis não responde após start"
  say "Redis  ✓"
fi

# 2. Ollama (só verificação — espera-se serviço de sistema)
if curl -fs http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  say "Ollama ✓"
else
  warn "Ollama não responde em :11434 — corre 'ollama serve' noutro terminal antes de gerar histórias"
fi

# 3. Limpa portas pendentes (uvicorn/vite anteriores)
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# 4. Backend
say "A iniciar backend (FastAPI :8000)…"
uvicorn backend.main:app --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
PIDS+=($!)
for _ in {1..30}; do
  curl -fs http://127.0.0.1:8000/healthz >/dev/null 2>&1 && break
  sleep 1
done
curl -fs http://127.0.0.1:8000/healthz >/dev/null 2>&1 \
  || fail "Backend não respondeu em 30 s — vê $LOG_DIR/backend.log"
say "Backend ✓"

# 5. Celery
say "A iniciar Celery worker…"
celery -A backend.core.celery_app:celery_app worker --loglevel=info --concurrency=1 \
  > "$LOG_DIR/celery.log" 2>&1 &
PIDS+=($!)
for _ in {1..20}; do
  grep -q "celery@.*ready" "$LOG_DIR/celery.log" 2>/dev/null && break
  sleep 1
done
grep -q "celery@.*ready" "$LOG_DIR/celery.log" 2>/dev/null \
  || warn "Celery demorou a ficar pronto — vê $LOG_DIR/celery.log"
say "Celery ✓"

# 6. Frontend
say "A iniciar frontend (Vite :5173)…"
( cd frontend && npm run dev > "$LOG_DIR/frontend.log" 2>&1 ) &
PIDS+=($!)
for _ in {1..40}; do
  curl -fs http://127.0.0.1:5173 >/dev/null 2>&1 && break
  sleep 1
done
curl -fs http://127.0.0.1:5173 >/dev/null 2>&1 \
  || fail "Frontend não respondeu em 40 s — vê $LOG_DIR/frontend.log (npm install correu?)"
say "Frontend ✓"

# 7. Browser (WSL → Windows; Linux → xdg-open)
URL="http://localhost:5173"
if command -v wslview >/dev/null 2>&1; then
  wslview "$URL" >/dev/null 2>&1 &
elif command -v cmd.exe >/dev/null 2>&1; then
  # ``start`` treats the first quoted argument as the WINDOW TITLE — so
  # ``start "http://..."`` would open a blank window with that title and
  # fall back to the browser homepage (often a hijacked search page).
  # The empty "" reserves the title slot so the URL goes through as the
  # target.
  cmd.exe /c start "" "$URL" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 &
fi

echo
printf "${B}${G}━━━ Living Memory pronto em ${URL} ━━━${N}\n"
printf "${D}Logs:    $LOG_DIR/{backend,celery,frontend}.log${N}\n"
printf "${D}Stop:    Ctrl+C${N}\n\n"

# Mantém o script vivo até receber sinal
wait
