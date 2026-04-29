# Changelog detalhado — Sessão de Frontend & Auth

> Registo das alterações feitas a este projeto durante o desenvolvimento da
> camada de apresentação React + endurecimento da camada de autenticação.
> Pensado para alimentar o capítulo "Implementação" do relatório de tese.

**Data:** abril 2026
**Versão:** 0.2.0 → 0.3.0
**Stack adicionada:** React 18 + TypeScript + Vite 5 + Tailwind CSS 3 + TanStack Query + Zustand + react-i18next + Sonner + Lucide

---

## 1 · Visão geral

A aplicação passou de "API + esqueleto vazio em `frontend/src`" para um
produto interativo completo. As alterações dividem-se em quatro
grandes blocos:

| Bloco | Resumo |
|---|---|
| **A. Frontend completo** | 13 páginas React, layout responsivo, dark/light/system, PT/EN |
| **B. Endurecimento auth** | Email + autocomplete bloqueado, mudar password, reset por email com SMTP opcional |
| **C. Robustez do pipeline** | Sweep de tarefas órfãs, alinhamento de schemas, deprecation de `datetime.utcnow` |
| **D. Operação** | Launcher único `start.sh`, CLI de reset, logs estruturados por componente |

---

## 2 · Frontend — arquitetura

### 2.1 Tecnologia escolhida

* **Vite 5** — bundler. Escolhido sobre Webpack/Parcel por velocidade
  do HMR (recarrega num clique sem perder estado).
* **TypeScript estrito** — `strict: true`, `noUnusedLocals`,
  `noUnusedParameters`. Apanha schema mismatches com o backend em
  *compile-time* em vez de em produção.
* **Tailwind CSS** — utilitário-first com `darkMode: "class"` para
  controlar tema via JavaScript em vez de `prefers-color-scheme`.
* **TanStack Query** (React Query) — gestão de cache + polling.
  Preferido sobre Redux porque o estado da aplicação é
  *server-state*, não *client-state*.
* **Zustand** — usado **só** para autenticação e tema (dois pequenos
  stores com `persist` middleware sobre `localStorage`).
* **react-i18next** — i18n com PT-PT como default e EN como fallback.

### 2.2 Estrutura de pastas

```
frontend/
├── index.html                    Vite entry, theme bootstrap inline
├── tailwind.config.js            Brand palette amber + animations
├── src/
│   ├── main.tsx                  QueryClientProvider, BrowserRouter, Toaster
│   ├── App.tsx                   Routes (públicas vs protegidas)
│   ├── index.css                 @apply do design system (.card, .btn-*, .input)
│   ├── i18n/
│   │   ├── index.ts              setLanguage(), persistência em "lm-lang"
│   │   ├── pt.ts                 strings PT-PT (default)
│   │   └── en.ts                 strings EN (mirror)
│   ├── lib/
│   │   ├── api.ts                axios instance + interceptor JWT + 401 logout
│   │   ├── hooks.ts              ~20 hooks de React Query (auth, media, stories…)
│   │   ├── photo.ts              photoUrl() — URL com token assinado
│   │   ├── types.ts              tipos espelhados do schema do backend
│   │   ├── utils.ts              cn(), formatBytes(), initials()
│   │   └── useTaskNotifications.ts   toast quando uma task termina
│   ├── store/
│   │   ├── auth.ts               Zustand persist — { token, user }
│   │   └── theme.ts              "light" | "dark" | "system" + matchMedia
│   ├── components/
│   │   ├── auth/
│   │   │   ├── RequireAuth.tsx   guard que redireciona para /login
│   │   │   └── AuthShell.tsx     wrapper centrado com gradiente + moldura
│   │   ├── brand/
│   │   │   └── Logo.tsx          SVG inline + wordmark "Living Memory"
│   │   ├── landing/
│   │   │   ├── LandingHeader.tsx     navbar fixo da landing pública
│   │   │   └── LandingSections.tsx   4 secções de marketing scrolláveis
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx     shell autenticado: Sidebar + Topbar + Outlet
│   │   │   ├── Sidebar.tsx       9 itens de navegação, mobile overlay
│   │   │   └── Topbar.tsx        toggle tema, avatar, logout
│   │   └── ui/
│   │       └── PageHeader.tsx    título serif + subtítulo + actions slot
│   └── pages/                    13 páginas (ver §2.3)
```

### 2.3 Páginas implementadas

| Rota | Página | Função |
|---|---|---|
| `/login` | LoginPage | Login + landing scrollável (4 secções de marketing) |
| `/register` | RegisterPage | Bootstrap do dono (1 conta por arquivo) |
| `/forgot-password` | ForgotPasswordPage | Pede email e dispara link de reset |
| `/reset-password?token=` | ResetPasswordPage | Form de nova password com validação de token |
| `/` | DashboardPage | 4 stats + ações rápidas + fotos/histórias recentes |
| `/library` | LibraryPage | Galeria com drag-drop, lightbox, navegação por teclado |
| `/family` | FamilyPage | Upload GEDCOM + lista pesquisável de pessoas |
| `/timeline` | TimelinePage | Eventos agrupados por ano com linha vertical |
| `/stories` | StoriesPage | Grid de histórias com preview |
| `/stories/:id` | StoryReaderPage | Leitor serif com drop-cap + botão "Gerar vídeo" |
| `/videos` | VideosPage | Cards com play overlay + modal player + status |
| `/generate` | GeneratePage | Wizard de 4 passos + modo sync/background |
| `/tasks` | TasksPage | Histórico de tarefas com cancel/delete + payload |
| `/settings` | SettingsPage | Conta + tema + idioma + health + change-password |
| `/404` | NotFoundPage | Catch-all |

### 2.4 Sistema de design

* **Brand amber** (`brand-50` `#FEF7EC` → `brand-900` `#281804`)
  evoca arquivo familiar, fotografias antigas, calor de lar.
* **Acentos secundários** introduzidos no `AuthShell`: emerald
  (sage — paz, continuidade) e rose (intimidade, confiança).
* **Tipografia** — Inter para UI (`font-sans`) e Fraunces para
  títulos serif e prosa do leitor (`font-serif`). Carregadas via
  Google Fonts com `preconnect` no `index.html`.
* **Animações** — `fade-in`, `slide-up`, `scale-in`, `shimmer`
  (skeletons), `bounce` (chevron de scroll). Tudo em
  `tailwind.config.js`.
* **Tema** — script inline no `<head>` lê `localStorage["lm-theme"]`
  antes de qualquer paint, evitando *flash of wrong theme*.

---

## 3 · Backend — alterações

### 3.1 Endpoints novos

| Método | Path | O que faz |
|---|---|---|
| `POST` | `/api/v1/auth/password` | Muda password (autenticado, exige password atual) |
| `POST` | `/api/v1/auth/forgot-password` | Inicia reset; dispara email ou regista no log |
| `POST` | `/api/v1/auth/reset-password` | Conclui reset com token de uso único |
| `GET`  | `/api/v1/media/{id}/file` | Serve bytes da foto (auth via header **ou** `?token=`) |
| `DELETE` | `/api/v1/media/{id}` | Apaga foto do disco + DB |
| `POST` | `/api/v1/tasks/{id}/cancel` | Revoga Celery task + marca `failed` |
| `DELETE` | `/api/v1/tasks/{id}` | Apaga entrada do histórico |
| `DELETE` | `/api/v1/tasks` | Limpa todas as tasks concluídas/falhadas |

### 3.2 Modelos de dados

* **Novo**: `password_reset_tokens` — `id`, `user_id`, `token_hash`
  (sha256, **nunca o plaintext**), `expires_at`, `used_at`,
  `created_at`. FK ao user com `ondelete=CASCADE`.

### 3.3 Configuração nova (settings.Config)

```python
FRONTEND_URL: str = "http://localhost:5173"
SMTP_ENABLED: bool = False
SMTP_HOST:    str  = "smtp.gmail.com"
SMTP_PORT:    int  = 587
SMTP_USERNAME: str = ""
SMTP_PASSWORD: str = ""
SMTP_FROM:    str  = "Living Memory <noreply@livingmemory.local>"
SMTP_USE_TLS: bool = True
PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 60
```

Tudo lido de `.env` na raiz do projeto via `pydantic_settings`.

### 3.4 Lifespan — sweep de tarefas órfãs

`backend/main.py` ganhou um hook que corre **uma vez** ao arranque
do FastAPI:

```python
async def _sweep_orphans() -> None:
    # Marca como 'failed' qualquer task que ficou pending/running
    # de um arranque anterior (worker não sobrevive a restart).
```

Antes deste fix, uma task que crashasse a meio ficava `running` para
sempre na BD. O Celery não a apanhava de novo (já tinha sido
*acked*) e o utilizador ficava sem feedback.

### 3.5 Email — `backend/core/email.py`

Sem dependências novas — usa `smtplib` da stdlib dentro de
`asyncio.to_thread()`. A função tem dois modos:

* **`SMTP_ENABLED=False`** (default): escreve `email_disabled_falling_back_to_log`
  no log estruturado com o corpo completo do email. Útil para
  desenvolvimento, demo de tese, e ambientes air-gapped.
* **`SMTP_ENABLED=True`**: envia mesmo via SMTP. Suporta TLS,
  autenticação opcional, e devolve `bool` para o caller decidir o
  que mostrar ao utilizador.

### 3.6 Auth dependency híbrido

`get_current_user_query_or_header` aceita o JWT em **`Authorization`
header** OU em **`?token=`** query string. Necessário para
`<img>`/`<video>` tags que não conseguem injetar headers
personalizados, mantendo os endpoints `serve_media_bytes` e
`download_video` autenticados.

---

## 4 · Segurança — decisões e justificações

### 4.1 Reset de password

| Decisão | Porquê |
|---|---|
| Token plaintext só **na resposta da resposta** (URL do email); BD guarda SHA-256 | Defesa em profundidade: leitura do SQLite não permite replay |
| Token de **uso único** via `used_at` | Bloqueia replays mesmo dentro do TTL |
| **TTL** configurável (default 60 min) | Janela curta limita risco de interceção |
| Resposta **uniforme** em `/forgot-password` (202 + mesma mensagem) | Impede enumeração de emails por timing/status |
| **Rate limit** via slowapi (3/min em forgot, 5/min em reset) | Mitigação contra brute-force |
| Token gerado com `secrets.token_urlsafe(48)` | CSPRNG, ~256 bits de entropia |

### 4.2 Mudar password autenticada

`POST /auth/password` exige `current_password` mesmo já tendo um
JWT válido. Padrão clássico: se um atacante apanhar o token mas não
souber a password atual, não consegue trocar a password e expulsar
o legítimo dono.

### 4.3 Browser autofill bloqueado

Login e Register usam:

* `autoComplete="off"` no `<form>`
* Campos com `name` aleatório (`lm-email-9af2`)
* Dois inputs honeypot escondidos (`x_user_dummy`, `x_pass_dummy`)
  com os `autocomplete` "username" e "current-password" — são eles
  que o browser preenche, deixando os reais limpos
* `useEffect` com `visibilitychange` + `pageshow` para limpar o
  estado React quando o utilizador volta à tab

Resultado: campos sempre vazios ao abrir/voltar à página, conforme
solicitado.

### 4.4 Auth no servir de ficheiros

Antes: `/api/v1/media/{id}/file` era público — qualquer pessoa na
rede local conseguia bytes das fotografias por URL. Agora exige JWT
via header **ou** `?token=`, e o frontend (`photoUrl`,
`videoUrl`) injeta o token automaticamente lendo do auth store.

---

## 5 · Bugs corrigidos

| # | Sintoma | Causa | Fix |
|---|---|---|---|
| 1 | Foto na biblioteca aparecia preta com ícone partido | `serve_media_bytes` chamava `record.filename` mas o modelo expõe `original_filename` | Renomeado |
| 2 | Ecrã preto ao abrir o app | `s.content.slice(...)` em DashboardPage; backend devolve `narrative` (não `content`) | Renomeado o campo no tipo TS + 4 sítios de uso |
| 3 | Tarefa "Em execução" para sempre | Worker antigo morreu sem libertar a row; sem hook de cleanup | `_sweep_orphans()` no lifespan |
| 4 | Vídeo "completed" não abria | Frontend esperava status `"ready"` mas backend usa `"completed"` | Tipo `VideoStatus` + chip colorido por estado |
| 5 | Erro 500 ao tentar registar | Owner já existia (404 vs 409 confuso) | UI agora detecta 409 e mostra "Faz login" |
| 6 | `datetime.utcnow()` deprecation warnings | Python 3.12+ retira o método | Substituído por `datetime.now(UTC)` em 9 ficheiros |
| 7 | i18n incompleto | Algumas keys em falta | Estendido pt.ts e en.ts |

---

## 6 · UX — melhorias específicas

* **Toasts automáticos** quando uma tarefa Celery termina —
  `useTaskNotifications` corre no `AppLayout`, observa o cache do
  React Query (`useTasks`) e dispara `toast.success`/`toast.error`
  em transições `pending|running → done|failed`. Inclui ação
  "Abrir" que navega para a história/vídeo.
* **Limpar histórico** em `/tasks` — botão único que apaga todas
  as tasks concluídas/falhadas em massa.
* **Lightbox do Library** — navegação por teclado (←/→/Esc),
  contador (n/total), descrição de IA da foto (se disponível).
* **Wizard de geração** — 4 passos com stepper visual; checks de
  validação antes de avançar; opção sync vs background.
* **Landing scrollável no `/login`** — 4 secções de marketing
  (Capacidades, Como funciona, Privacidade, CTA) acessíveis por
  scroll natural ou pelos âncoras do navbar fixo.

---

## 7 · Operação

### 7.1 `start.sh` — launcher unificado

Substitui os 4 terminais que o utilizador precisava antes
(redis + uvicorn + celery + npm). Faz:

1. Ativa `venv`
2. Verifica/inicia Redis (`redis-cli ping` → fallback `sudo service`)
3. Avisa se Ollama não responde (não bloqueia)
4. Liberta portas 8000 e 5173 caso fiquem presas
5. Arranca **uvicorn** em background, espera por `/healthz`
6. Arranca **Celery worker** em background, espera por `celery@... ready`
7. Arranca **Vite** em background, espera por `:5173`
8. Abre o **browser** automaticamente (wslview / cmd.exe / xdg-open)
9. `Ctrl+C` mata tudo limpo (trap + `wait`)

Logs separados em `logs/launcher/{backend,celery,frontend}.log`.

### 7.2 CLI de reset — `python -m backend.scripts.reset_password`

Para o caso de o utilizador se esquecer da password e o SMTP estar
desligado. Aceita `--username` (default: owner) e `--password`
(default: pede via `getpass`, oculta input). Atualiza só o hash; os
dados ficam intactos.

---

## 8 · Internacionalização

Toda a UI está disponível em **PT-PT** (default) e **EN** com
toggle em `/settings`. Strings em `src/i18n/pt.ts` e `en.ts`. A
língua persiste em `localStorage["lm-lang"]` e o atributo
`<html lang>` é sincronizado.

---

## 9 · Como testar

### 9.1 Fluxo "happy path"

```bash
~/family-stories/start.sh
# browser abre em http://localhost:5173
```

1. Cria conta em `/register` (email + password ≥ 8 chars)
2. `/library` → drag-drop de 5-10 fotos
3. `/family` → upload de um GEDCOM
4. `/generate` → wizard de 4 passos → submit em background
5. `/tasks` — verás a task `pending → running → done` com toast
6. `/stories/:id` — lê com drop-cap → botão "Gerar vídeo"
7. `/videos` — esperar status `Pronto` → play modal

### 9.2 Reset de password (sem SMTP, modo log-only)

1. `/login` → "Esqueceste-te?"
2. Mete o email, submete
3. Abre `logs/launcher/backend.log` e procura
   `email_disabled_falling_back_to_log` — vais ver o body completo
   do email com o link
4. Copia o link → cola no browser → define nova password

### 9.3 Reset com SMTP real (Gmail)

Cria `.env` na raiz:

```env
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=oteuemail@gmail.com
SMTP_PASSWORD=app-password-do-gmail
SMTP_FROM=Living Memory <oteuemail@gmail.com>
SMTP_USE_TLS=true
FRONTEND_URL=http://localhost:5173
```

> Gmail exige uma **App Password**, não a tua password normal.
> Conta Google → Segurança → Verificação em 2 etapas → App passwords.

Reinicia o `start.sh` e o email passa a chegar mesmo à inbox.

---

## 10 · Trabalho que ficou por fazer

Lista honesta do que **não** está feito mas faz sentido para o
relatório/defesa:

* **Métricas** — não há dashboard de tempos de geração, taxa de
  sucesso por template, qualidade do RAG. Os dados existem em
  `task_records.created_at/updated_at` e em `stories.facts_used`,
  basta extrair.
* **Multi-utilizador** — o sistema continua single-owner. A tabela
  `users` suporta `is_owner` mas não há flow de convite.
* **Docker compose** — tinhas pedido para preparar para Postgres;
  ficámos por SQLite. Os modelos SQLAlchemy estão prontos para
  trocar a connection string.
* **Testes E2E** — a suite pytest (37 testes) cobre backend.
  Testes Playwright/Cypress para o frontend não foram adicionados.
* **Acessibilidade** — labels ARIA estão lá, navegação por teclado
  no lightbox sim, mas falta auditoria com axe-core e contraste
  validado em WCAG AA.

---

## 11 · Glossário rápido

| Termo | Significado neste projeto |
|---|---|
| **M1** | Módulo 1 — ingestão multimodal (fotos + GEDCOM) |
| **M2** | Módulo 2 — organização temporal (datas + grafo familiar) |
| **M3** | Módulo 3 — geração narrativa (LLM + RAG) |
| **M4** | Módulo 4 — geração multimédia (Ken Burns + TTS + MP4) |
| **Owner** | Único utilizador autenticado por arquivo |
| **Task fantasma** | Linha em `task_records` cujo Celery worker já não existe |
| **Local-first** | Premissa do projeto: nada sai da máquina por defeito |
| **Log-only mode** | SMTP desligado: links de reset escritos no log |

---

*Atualizado em abril de 2026 durante a sessão de finalização do
frontend e endurecimento da camada de autenticação.*
