# Living Memory — Family Stories AI

Sistema que transforma automaticamente um **arquivo familiar** (fotografias,
documentos digitalizados e árvores genealógicas) num **produto narrativo
multimédia**: linhas temporais, histórias escritas e **vídeos documentais
narrados** — sem que o utilizador tenha de escrever textos ou descrever o
conteúdo à mão.

> Projeto de tese — Universidade da Beira Interior, Departamento de Informática.

---

## 1. O que o sistema faz

A partir de fotos + árvore genealógica (GEDCOM) + documentos, produz:

1. **Factos estruturados** de cada foto — data e local (EXIF/GPS), texto de
   documentos (OCR) e uma descrição do conteúdo visual (IA de visão).
2. **Linha temporal** da família, ordenada por data e ligada a pessoas reais.
3. **Narrativas escritas** em português europeu, geradas por IA com base nos
   factos reais (nunca inventa pessoas nem relações).
4. **Vídeos documentais** com as fotografias, voz narrada, transições
   cinematográficas e legendas sincronizadas.

O sistema é uma **aplicação Web completa** que corre de forma idêntica em
ambiente local e online, a **custo essencialmente nulo** (usa camadas
gratuitas de serviços de IA).

---

## 2. O *pipeline* (como funciona por dentro)

O processamento organiza-se em quatro módulos sequenciais:

| Módulo | Faz |
|---|---|
| **M1 — Ingestão** | Lê os ficheiros; extrai EXIF/GPS, faz OCR (Tesseract) e descreve a foto com o **Gemini Vision**; importa árvores **GEDCOM**. |
| **M2 — Organização temporal** | Resolve datas incompletas e constrói o **grafo de parentesco** (quem é quem). |
| **M3 — Geração narrativa** | Escreve a história com um **LLM** (Groq → Ollama → Gemini), ancorada nos factos via **RAG** + grafo, e segmenta-a em **cenas** ligadas a fotos. |
| **M4 — Geração multimédia** | Converte a narrativa num **vídeo MP4** com enquadramento cinematográfico, **voz** e **legendas**. |

**Estratégia de IA (custo nulo):** texto pelo **Groq** (Llama 3.3 70B, na
nuvem) → **Ollama** (local, offline) → **Gemini** como alternativas; visão
sempre pelo **Gemini**. Assim, texto e visão repartem-se por serviços
gratuitos distintos.

---

## 3. Funcionalidades e opções

- **Biblioteca** de fotografias com *drag-and-drop* e re-análise sob procura.
- **Família:** importar GEDCOM, árvore interativa (pesquisar, destacar
  linhagem, exportar imagem), editor manual e "criação rápida de árvore".
- **Linha Temporal** automática.
- **Gerar história**, com escolha de:
  - **Tema/tom** (6 temas + personalizado);
  - **Idioma** (Português europeu / Inglês);
  - **Comprimento**: *curta* (~1 min), *média* (~2-3), *longa* (~4-5) ou
    *épica* (~6-8);
  - **Fotografias** específicas (ou automáticas).
- **Leitor de histórias:** editar, **regenerar com *feedback***, favoritar,
  pesquisar e **exportar para PDF**.
- **Vídeo:** escolher a **voz** (masculina/feminina), ligar/desligar
  **legendas** e o seu tamanho.
- **Projetos:** organizar fotos/histórias/vídeos por coleção; um projeto pode
  **reutilizar fotos já analisadas** da biblioteca (sem re-analisar).
- **Idioma da interface** comutável (PT/EN) e tema claro/escuro.

---

## 4. Pré-requisitos

- **Python 3.12+** e **Node.js 18+**
- **FFmpeg** (montagem de vídeo) e **Tesseract** (OCR) instalados no sistema
- Opcional: **Redis** (fila Celery — o sistema funciona sem ele, com um
  executor interno) e **Ollama** (LLM local)
- Contas gratuitas: **Supabase** (auth + base de dados + *storage*),
  **Google Gemini** e **Groq** (chaves de API)

---

## 5. Instalação e configuração

```bash
# 1. Clonar e entrar
git clone <repo> && cd family-stories

# 2. Backend (Python)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Frontend
cd frontend && npm install && cd ..
```

Cria um ficheiro **`.env`** na raiz com as chaves (nunca as escrevas no
código nem as partilhes):

```dotenv
# --- IA (texto + visão) ---
GEMINI_API_KEY=...            # aistudio.google.com  (visão + fallback de texto)
GROQ_API_KEY=gsk_...          # console.groq.com     (texto principal, grátis)

# --- Supabase (auth, base de dados, storage) ---
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DB_URL=postgresql://...:6543/postgres   # pooler (porta 6543)

# --- Opcional ---
OLLAMA_BASE_URL=http://localhost:11434   # LLM local (se tiveres Ollama)
SECRET_KEY=<uma-string-aleatória-longa>
```

**Base de dados:** corre o *schema* SQL uma única vez no Supabase
(SQL Editor) — os ficheiros estão em `backend/sql/` (por ordem: `0001`,
`0002`, …). **Nunca voltes a correr o `0001_initial.sql` numa BD com
dados** — ele apaga tudo (já vem com os `DROP` comentados por segurança).

---

## 6. Como executar

**Forma simples (tudo de uma vez):**

```bash
./start.sh
```

Arranca o Redis (se existir), o **backend** (FastAPI em `:8000`) e o
**frontend** (Vite em `:5173`), espera que respondam e abre o *browser* em
`http://localhost:5173`. `Ctrl+C` termina tudo.

**Forma manual (terminais separados):**

```bash
# Backend
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

Saúde do sistema: `http://localhost:8000/healthz`.

---

## 7. Como usar — passo a passo

1. **Registar / entrar** (a autenticação é gerida pelo Supabase).
2. **Biblioteca → Carregar** as fotografias (arrasta ou escolhe). O sistema
   analisa-as em segundo plano (aparece "a analisar"); quando termina, cada
   foto tem descrição, data e local.
3. **Família → Importar GEDCOM** (opcional) para trazer a árvore genealógica.
   A narrativa fica muito mais rica com as relações e as notas das pessoas.
4. **Gerar** → escolhe o **tema**, o **tom**, o **idioma**, o **comprimento**
   e (opcional) as **fotografias**. Carrega em gerar.
5. **Histórias** → lê, edita ou **regenera com feedback** ("mais curta",
   "foca-te no avô João", etc.).

### Como gerar um vídeo

1. Cria (ou abre) uma **história** no leitor.
2. Carrega em **"Gerar vídeo"**.
3. Antes de gerar, no assistente escolhes a **voz** (masculina/feminina) e se
   queres **legendas** (e o tamanho).
4. O sistema sintetiza a narração, sincroniza cada fotografia com a parte da
   narração que lhe corresponde (as fotos **alternam** quando a narração é
   longa e há poucas fotos), aplica transições e produz um **MP4**.
5. Vê o resultado em **Vídeos**, com *player* e botão de descarregar. As
   legendas são uma faixa comutável no leitor e ficam embutidas no ficheiro
   descarregado.

> Nota: o *render* de vídeo é feito **localmente** (o plano gratuito da nuvem
> não tem memória para 720p); o ficheiro final é depois carregado para o
> *storage* e reproduzido a partir de lá.

---

## 8. *Deploy* online (opcional)

- **Backend:** Render (Docker) — `git push` faz o *deploy* automático.
- **Frontend:** Vercel — `git push` reconstrói.
- **Supabase:** auth, base de dados e *storage*.
- **Keep-alive:** aponta um *cron* (ex.: cron-job.org) ao endpoint
  `…/healthz` a cada ~10 min — mantém o backend acordado **e** a base de
  dados ativa (evita a pausa do plano gratuito).

---

## 9. Testes e cópia de segurança

```bash
# Testes unitários (56 a passar)
venv/bin/python -m pytest tests/unit -q

# Backup de todos os dados para JSON (o free tier não tem restauro)
venv/bin/python -m backend.scripts.backup_data   # cria backups/backup_*.json
```

---

## 10. Stack técnico

- **Backend:** FastAPI (assíncrono), SQLAlchemy, asyncpg, Celery/Redis
  (opcional), structlog, slowapi.
- **Frontend:** React + TypeScript, Vite, TanStack Query, Zustand, React Flow.
- **IA:** Groq (Llama 3.3 70B), Ollama (local), Google Gemini (texto + visão),
  ChromaDB (RAG), edge-tts (voz).
- **Multimédia:** MoviePy + FFmpeg, exifread, Tesseract (OCR).
- **Nuvem:** Render (backend), Vercel (frontend), Supabase (auth/DB/storage).

---

## 11. Estrutura do projeto

```
backend/        API FastAPI + módulos M1–M4 + modelos + scripts + sql/
frontend/       Aplicação React/TypeScript
tests/          Testes unitários (pytest)
Projetos/       Relatório de tese (LaTeX)
start.sh        Arranque de tudo num comando
```
