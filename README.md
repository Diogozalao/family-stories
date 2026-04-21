# Sistema de Geração Automática de Histórias Familiares

Fluxo Básico (Sempre que alteras ficheiros)
git add .              # 1. Adiciona TODAS as alterações
git commit -m "msg"    # 2. Cria um snapshot com descrição
git push               # 3. Envia para o GitHub


Ver o que mudou antes de adicionar:
    git status             # Vê quais ficheiros foram alterados/adicionados
    git diff               # Vê o conteúdo das alterações


Adicionar apenas ficheiros específicos (em vez de git add .)
    git add backend/app.py        # Apenas um ficheiro
    git add backend/              # Toda uma pasta
    git add *.py                  # Todos os ficheiros .py



------------------------------------
rm -f ~/family-stories/family_stories.db
rm -f ~/family-stories/data/raw/photos/*


fuser -k 8000/tcp
cd ~/family-stories
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000



# Family Stories AI

Sistema local de geração automática de histórias e vídeos documentais a partir do arquivo familiar (fotografias, documentos, árvore genealógica).

**Projeto de tese** — Universidade da Beira Interior, 2026.

---

## O que o sistema faz

Pega em fotografias antigas + árvore genealógica (GEDCOM) + documentos digitalizados e produz, de forma completamente local (sem enviar dados para a nuvem):

1. **Factos estruturados** extraídos automaticamente das fotos (EXIF, OCR, análise visual).
2. **Linha temporal** coerente da família, ordenada por data, ligada a pessoas reais.
3. **Narrativas escritas** em português europeu, geradas por LLM com contexto familiar real (RAG + grafo genealógico).
4. **Vídeos documentais** com as fotos, voz narrada, transições cinematográficas e legendas.

Tudo fica na máquina do utilizador. Nada sai para servidores externos (exceto opcionalmente o Gemini como fallback do LLM).

---

## Estado atual (abril 2026)

### Módulos funcionais

| Módulo | Estado | Descrição |
|---|---|---|
| **M1 — Ingestão Multimodal** | ✅ | Upload de fotos, extração EXIF, OCR (Tesseract), análise visual com Gemini Vision, parsing GEDCOM |
| **M2 — Organização Temporal** | ✅ | Validação de datas, resolução de conflitos, construção de grafo familiar (NetworkX) |
| **M3 — Geração Narrativa** | ✅ | LLM local (Llama 3.1 via Ollama), RAG com ChromaDB, 6 templates PT-PT, fallback para Gemini Flash |
| **M4 — Geração Multimédia** | ✅ | Ken Burns com letterbox não-destrutivo, crossfades, TTS europeu (gTTS), exportação MP4 H.264 |

### Infraestrutura (Fase A — concluída)

- ✅ Autenticação JWT (bcrypt + python-jose), modelo single-owner
- ✅ Rate limiting por IP (slowapi)
- ✅ Validação de uploads (libmagic + magic bytes + limites de tamanho)
- ✅ Logging estruturado (structlog, stdout + ficheiro rotativo)
- ✅ Health checks profundos (`/healthz` sonda DB, Ollama, Gemini, Redis, ChromaDB, disco)
- ✅ Fila assíncrona com Celery + Redis para tarefas longas
- ✅ Endpoints de polling de estado (`/api/v1/tasks/{id}`)
- ✅ Suite pytest (37 testes a passar — unit + integration)

### Por fazer

- ⏳ **Fase B — Frontend React**: UI completa (login, upload drag-and-drop, player de vídeo, lista de narrativas). Actualmente só existe o esqueleto em `frontend/src/`.
- ⏳ Dockerização
- ⏳ Métricas para a tese (tempos de geração, qualidade de narrativa, benchmark de templates)

---

## Stack técnico

### Backend
- **FastAPI** (async) + **SQLAlchemy** (aiosqlite)
- **Celery** + **Redis** — fila de tarefas
- **slowapi** — rate limiting
- **structlog** — logs estruturados
- **bcrypt** + **python-jose** — auth JWT

### IA / ML
- **Ollama** (Llama 3.1) — LLM local
- **Gemini Flash** — fallback remoto opcional
- **ChromaDB** — vector store para RAG
- **sentence-transformers** — embeddings
- **Tesseract** — OCR
- **NetworkX** — grafo familiar

### Multimédia
- **MoviePy** + **FFmpeg** — composição de vídeo
- **Pillow** — processamento de imagem (letterbox + Gaussian blur + Ken Burns)
- **gTTS** — text-to-speech português europeu (`tld="pt"`)

### Persistência
- **SQLite** (`family_stories.db`) — metadados
- **Sistema de ficheiros** (`data/`) — fotos, vídeos, áudio, grafo genealógico
- **ChromaDB** (`data/processed/chroma_db/`) — embeddings RAG

---

## Estrutura do projeto

```
family-stories/
├── backend/
│   ├── api/routes/          # auth, upload, timeline, narrative, genealogy,
│   │                        # multimedia, tasks, health
│   ├── core/                # config, database, security, auth, logging,
│   │                        # rate_limit, upload_validator, celery_app
│   ├── models/              # user, media, timeline, narrative, video, task
│   ├── modules/
│   │   ├── m1_ingestion/    # processor, exif, ocr, gedcom, gemini_analyzer
│   │   ├── m2_temporal/     # date_resolver, family_graph, timeline_builder
│   │   ├── m3_narrative/    # generator, llm_client, rag_system, templates
│   │   └── m4_multimedia/   # processor, video_builder, tts_generator
│   ├── schemas/             # Pydantic request/response models
│   ├── tasks/               # Celery task definitions
│   └── main.py              # FastAPI entry point
├── frontend/                # React (ainda por construir — Fase B)
├── data/
│   ├── raw/                 # photos, gedcom, documents (input do utilizador)
│   └── processed/           # videos, audio, chroma_db, family_graph.json
├── tests/
│   ├── unit/                # security, upload_validator, date_resolver,
│   │                        # family_graph, templates, video_builder
│   └── integration/         # auth_routes, health_route
├── logs/                    # ficheiros de log rotativos
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Como correr o projeto

### Pré-requisitos (uma única vez)
```bash
sudo service redis-server start     # Redis
ollama serve                        # Ollama (noutro terminal)
ollama pull llama3.1                # Modelo LLM local
```

### Arranque (3 terminais)

**Terminal 1 — Servidor FastAPI:**
```bash
cd ~/family-stories
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Worker Celery (só para `mode=background`):**
```bash
cd ~/family-stories
source venv/bin/activate
celery -A backend.core.celery_app:celery_app worker --loglevel=info --concurrency=1
```

**Terminal 3 — Interagir com a API:**
```bash
# Abre http://127.0.0.1:8000/docs no browser (Swagger UI)
# Ou usa curl — ver "Fluxo típico" abaixo.
```

---

## Fluxo típico de utilização

### 1. Criar o dono do arquivo (primeira vez)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"diogo","password":"apalavrapassealonga"}'
```

### 2. Login para obter token JWT
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -d "username=diogo&password=apalavrapassealonga"
```

### 3. Enviar fotografias
```bash
export TOKEN="cola-aqui-o-token"

curl -X POST http://127.0.0.1:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@caminho/para/foto.jpg"
```

### 4. Importar árvore genealógica (GEDCOM)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/genealogy/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@caminho/para/arvore.ged"
```

### 5. Indexar factos no RAG
```bash
curl -X POST http://127.0.0.1:8000/api/v1/narrative/index \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Gerar narrativa
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/narrative/generate?mode=sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Memórias do Avô","event_type":"default","query":"família","person_ids":[]}'
```

### 7. Gerar vídeo documental
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/multimedia/generate/1?mode=sync" \
  -H "Authorization: Bearer $TOKEN"
# O MP4 fica em data/processed/videos/
```

---

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Info geral + lista de módulos |
| GET | `/health` | Liveness (200 se servidor está vivo) |
| GET | `/healthz` | Deep health — sonda todas as dependências |
| POST | `/api/v1/auth/register` | Criar dono do arquivo (1× apenas) |
| POST | `/api/v1/auth/login` | Login → JWT |
| GET | `/api/v1/auth/me` | Perfil do utilizador autenticado |
| POST | `/api/v1/upload` | Upload fotografia |
| POST | `/api/v1/upload/batch` | Upload múltiplo |
| GET | `/api/v1/media` | Listar ficheiros enviados |
| POST | `/api/v1/genealogy/upload` | Importar GEDCOM |
| GET | `/api/v1/timeline` | Linha temporal da família |
| GET | `/api/v1/narrative/templates` | 6 templates disponíveis |
| POST | `/api/v1/narrative/index` | Indexar factos no RAG |
| POST | `/api/v1/narrative/generate` | Gerar história (sync/background) |
| GET | `/api/v1/narrative/stories` | Listar narrativas geradas |
| POST | `/api/v1/multimedia/generate/{story_id}` | Gerar vídeo (sync/background) |
| GET | `/api/v1/multimedia/videos` | Listar vídeos |
| GET | `/api/v1/multimedia/video/{filename}` | Descarregar MP4 |
| GET | `/api/v1/tasks` | Listar tarefas Celery |
| GET | `/api/v1/tasks/{id}` | Estado de uma tarefa |

Documentação interativa completa: **http://127.0.0.1:8000/docs**

---

## Testes

```bash
cd ~/family-stories
source venv/bin/activate
pytest -W ignore::DeprecationWarning          # todos os testes
pytest tests/unit -v                          # só unit tests
pytest tests/integration -v                   # só integration
pytest --cov=backend --cov-report=term-missing  # com cobertura
```

Resultado atual: **37/37 testes a passar**.

---

## Rate limits (por IP)

| Endpoint | Limite |
|---|---|
| Por defeito | 100/minuto |
| Upload | 20/minuto |
| Geração (narrativa + vídeo) | 5/minuto |
| Login | 10/minuto |
| Register | 3/minuto |

---

## Comandos úteis

### Git
```bash
git status                 # ver o que mudou
git add <ficheiro>         # preparar alteração
git commit -m "mensagem"   # snapshot
git push                   # enviar para GitHub
```

### Manutenção
```bash
fuser -k 8000/tcp                   # matar processo na porta 8000
rm -f family_stories.db             # limpar base de dados
rm -rf data/processed/*             # limpar outputs gerados
tail -f logs/app.log                # seguir logs em tempo real
```

### Verificar dependências
```bash
redis-cli ping                       # Redis vivo?
curl http://localhost:11434/api/tags # Ollama vivo?
curl http://127.0.0.1:8000/healthz   # tudo vivo?
```

---

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---|---|---|
| `401 Unauthorized` | Token expirado (7 dias) ou em falta | Fazer `/auth/login` de novo |
| `409 Conflict` no register | Dono já existe | Usar `/auth/login` |
| `429 Too Many Requests` | Rate limit atingido | Esperar 1 minuto |
| Task fica `pending` para sempre | Worker Celery não está a correr | Arrancar Terminal 2 |
| `/healthz` mostra ollama: error | Ollama não está a correr | `ollama serve` |
| `/healthz` mostra redis: error | Redis não está a correr | `sudo service redis-server start` |
| Vídeo demora muito | Normal em CPU — 1 a 5 min | Ter paciência ou usar `mode=background` |
| Narrativa em português do Brasil | Templates corretos, LLM derivou | Repetir geração (PT_PT_RULES está em todos os templates) |

---

## Notas de desenvolvimento

- O `venv/` pesa ~5 GB por causa das dependências CUDA do PyTorch arrastadas pelo `sentence-transformers`. Pode-se reinstalar PyTorch em modo CPU-only para poupar ~4 GB sem perda de funcionalidade.
- A base de dados (`family_stories.db`) é SQLite e persiste tudo entre sessões.
- O grafo genealógico é serializado em `data/processed/family_graph.json`.
- Os logs persistem em `logs/app.log` com rotação automática (10 MB × 5 ficheiros).
