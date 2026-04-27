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