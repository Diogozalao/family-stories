Terminal 1 — Redis (só 1 vez por sessão):

    sudo service redis-server start


Apagar contiudos anteriorees:
fuser -k 8000/tcp
rm -f ~/family-stories/family_stories.db
rm -f ~/family-stories/data/raw/photos/*
# arrancar o backend outra vez (Terminal 2 do guião anterior)


Terminal 2 — Backend (API)

fuser -k 8000/tcp
cd ~/family-stories
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000



Terminal 3 — Celery worker (tarefas em background: gerar história/vídeo)

cd ~/family-stories
source venv/bin/activate
celery -A backend.core.celery_app:celery_app worker --loglevel=info --concurrency=1



Terminal 4 — Frontend (novo)

cd ~/family-stories/frontend
npm run dev



---------------------------------------

~/family-stories/start.sh
ou só:


cd ~/family-stories && ./start.sh


O que faz, por ordem:
    Ativa venv
    Redis — verifica se responde; se não, sudo service redis-server start
    Ollama — só verifica (avisa se não estiver, não bloqueia)
    Liberta portas 8000 e 5173 caso fiquem presas
    Backend (uvicorn) — espera até /healthz responder
    Celery worker — espera até ver celery@... ready no log
    Frontend (Vite) — espera até a porta 5173 responder
    Abre o browser automaticamente em http://localhost:5173
    Fica vivo. Ctrl+C mata os 3 processos + liberta portas.