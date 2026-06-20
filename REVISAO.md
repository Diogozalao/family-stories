# Revisão ponta-a-ponta — Family Stories / Living Memory

> Revisão técnica do projeto completo (backend + frontend), feita a 2026-06-20.
> Lista o que está bem, **onde podem surgir erros**, e o que melhoraria — por
> ordem de prioridade. No fim: a feature de **foto por pessoa** que foi
> adicionada nesta sessão e como a por em produção.

---

## 1. Como o sistema funciona (fluxo real, ponta a ponta)

```
Utilizador (browser, Vercel)
   │  React + Vite + TanStack Query + Zustand + react-router
   ▼
Backend FastAPI (Render free)  ──auth JWT (Supabase)──►  Supabase Postgres + Storage
   │
   ├─ M1 Ingestão:   upload → Storage; análise IA diferida (Gemini Vision) + OCR (Tesseract) + EXIF
   ├─ M2 Temporal:   timeline a partir das fotos; grafo familiar (NetworkX)
   ├─ M3 Narrativa:  LLMClient (Ollama→Gemini→Groq) + templates + (RAG opcional)
   └─ M4 Multimédia: vídeo (MoviePy/FFmpeg) + voz (edge-tts/gTTS), tudo local
```

**Fonte de verdade:** Supabase Postgres (persistente). O **disco do Render é
efémero** — apagado a cada deploy/restart. Tudo o que depende de ficheiros locais
no Render é **frágil**. Esta é a causa de vários problemas abaixo.

---

## 2. Bugs e riscos confirmados (por severidade)

### 🔴 ALTO

**2.1. O grafo familiar em disco ainda é lido em 2 endpoints — fica vazio em produção.**
Corrigi o **gerador de narrativas** para ler a árvore da BD, mas
[`genealogy.py` `get_person`](backend/api/routes/genealogy.py) (linha ~251) e
[`get_graph`](backend/api/routes/genealogy.py) (linha ~273) **ainda carregam o
JSON do disco** (`graphs/{user}.json`). No Render, após um restart, esse ficheiro
não existe → `get_person` devolve **relatives vazios** e `/graph` devolve um grafo
**vazio**. O `_rebuild_graph_from_db` continua a escrever um JSON que já quase
ninguém lê de forma fiável.
→ **Fix recomendado:** tornar `get_person`/`get_graph` *DB-backed* (construir o
grafo a partir de `persons`+`relationships`, como já faz o gerador) e **remover de
vez** o JSON em disco e o `_rebuild_graph_from_db`. (O editor da árvore usa
`/genealogy/tree`, que já é DB-backed — por isso a UI principal não sofre, mas
estes dois endpoints sim.)

**2.2. Visão (fotos) tem ~20 pedidos/dia no free tier, sem fallback.**
`gemini-2.5-flash` é o único modelo de visão que o free tier serve, e dá ~20/dia.
Para 20 fotos/dia ficas **no limite**, sem rede de segurança (o Groq não faz
visão). Risco real de falhas em dias de uso intenso.
→ **Opções:** lotes pequenos de re-análise; ou €25 de pré-pago (resolve de vez).

### 🟠 MÉDIO

**2.3. Suite de testes partida (pré-existente).**
`tests/unit/test_security.py` e `tests/conftest.py` importam
`backend.core.security`, que **deixou de existir** após a migração da auth para
Supabase. A suite **nem arranca** → a afirmação **"37 testes OK"** do relatório
**não é verdadeira** hoje. Decisão pendente: **arranjar os testes** ou **corrigir
o relatório**.

**2.4. RAG/ChromaDB está desligado em produção.**
No `requirements.txt`, o `chromadb` está **comentado** (para o build do Render
caber nos 15 min). Logo, em produção a "RAG" é um *stub*: `search_media_ids`
devolve `[]` e usa-se simplesmente **todas** as fotos. O endpoint
`/narrative/index` não faz nada útil em prod. O relatório descreve RAG com
ChromaDB — **em produção isso não corre**. (Funciona em local se reativares o
`chromadb`.) → Honestidade no relatório, ou reativar com um vetor mais leve.

**2.5. Redis/Celery inertes em produção.**
Narrativas e vídeos são forçados a **síncrono** (boa decisão para o free tier),
mas isso deixa o caminho *background*/Celery decorativo, e o health-check reporta
`status: error` por causa do `redis`/`ollama` ausentes — **cosmético**, mas
confunde monitorização (ex.: o cron-job.org que mantém a instância acordada).
→ Em produção, não contar `ollama`/`redis` como *failures* (são ausências
propositadas), ou marcá-los como `warning`.

**2.6. Texto online faz 2 chamadas Gemini falhadas antes do Groq.**
`gemini-2.0-flash` dá `limit:0` no free tier, mas continua a ser o motor primário
de texto → cada narrativa online tenta o Gemini 2× (falha rápido), depois cai no
Groq. Funciona, mas desperdiça latência.
→ Detetar `RESOURCE_EXHAUSTED`/`limit:0` e ir direto ao Groq; ou usar
`gemini-2.5-flash` com *thinking* desligado para texto.

### 🟡 BAIXO

- **2.7.** `useDeleteAccount` (frontend) **lança erro** — eliminar conta não está
  implementado (precisa de permissões admin no backend).
- **2.8.** Mudar password **não verifica a password atual** (limitação do
  Supabase, documentada no código).
- **2.9.** `photo_media_id` (a nova feature) é um *soft pointer* sem FK: se
  apagares a foto, o avatar fica pendente. Tratado como "sem avatar", mas o ideal
  é **limpar o `photo_media_id`** das pessoas no `delete_media`.
- **2.10.** Etiquetagem foto↔pessoa só existe **do lado da foto**
  (`useSetMediaPersons`). Com os avatares novos, faria sentido etiquetar também
  **do lado da pessoa**.

---

## 3. O que eu melhoraria (estrutura e UX)

### Backend
- **Eliminar o grafo em disco** (ver 2.1) — uma só fonte de verdade (BD) elimina
  toda uma classe de bugs do disco efémero.
- **Camada de serviço:** a lógica de negócio vive nas rotas; extrair *services*
  (ex.: `NarrativeService`, `GenealogyService`) tornaria os testes mais fáceis e
  as rotas mais finas.
- **Migrações versionadas reais** (Alembic) em vez de SQL manual em `backend/sql/`
  — reduz o risco de a BD e os modelos divergirem.

### Frontend (a estrutura que pediste para melhorar)
- **Dividir ficheiros grandes:** `FamilyEditor.tsx` junta `PersonForm`,
  `PedigreeWizard`, o `PhotoPicker` e o editor principal num só ficheiro — separar
  em `family/` (um componente por ficheiro) melhora a legibilidade e o *code-split*.
- **Padronizar estados de loading/erro/vazio:** criar componentes reutilizáveis
  (`<Loading/>`, `<EmptyState/>`, `<ErrorState/>`) e usá-los em todas as páginas —
  hoje cada página resolve isto à sua maneira.
- **Camada de API tipada por domínio:** os `hooks.ts` (600 linhas) podiam ser
  divididos por domínio (`hooks/media.ts`, `hooks/genealogy.ts`, …) e os endpoints
  centralizados num módulo de *queries*.
- **Botão "Re-analisar fotos"** na Biblioteca (o endpoint
  `POST /narrative/reanalyze-photos` já existe) — para repor descrições sem ter de
  chamar a API à mão.
- **Etiquetar pessoas a partir da foto e da pessoa** (ver 2.10), e mostrar na
  Biblioteca quem está etiquetado em cada foto.
- **Testes de frontend** (Vitest + Testing Library) — não há nenhum.
- **Acessibilidade:** alguns botões só com ícone não têm `aria-label`.

### Produto / IA
- **Mostrar ao utilizador o que a IA "sabe"** antes de gerar (factos por foto +
  árvore) — dá-lhe controlo e evita surpresas como a narrativa inventada.
- **Pré-visualização do prompt** (modo avançado) para a tese — mostra que a
  geração é *grounded* em dados reais.

---

## 4. Feature adicionada nesta sessão — foto por pessoa

Implementada e validada (backend importa OK; frontend `tsc` exit 0).

**Backend**
- `Person.photo_media_id` (soft pointer) — [models/timeline.py](backend/models/timeline.py).
- Migração SQL **0009** — [sql/0009_person_photo.sql](backend/sql/0009_person_photo.sql) (idempotente).
- `PATCH /genealogy/persons/{id}` aceita `photo_media_id` (valida que a foto é do
  dono; `null` limpa) — [genealogy.py](backend/api/routes/genealogy.py).
- `photo_media_id` exposto no serializador → chega ao editor e à árvore.

**Frontend** — [FamilyEditor.tsx](frontend/src/components/family/FamilyEditor.tsx), [FamilyTree.tsx](frontend/src/components/family/FamilyTree.tsx)
- `PersonForm`: secção de **foto** com avatar + "Escolher foto" (grelha da
  Biblioteca) + "Remover".
- **Avatar** na lista de pessoas do editor e **nos nós da árvore** (cara redonda).
- *Fallback* para iniciais quando não há foto. i18n pt/en atualizado.

**Como pôr a funcionar**
1. **Correr a migração no Supabase** (SQL Editor):
   ```sql
   ALTER TABLE persons ADD COLUMN IF NOT EXISTS photo_media_id BIGINT;
   ```
   *(Sem isto, o backend dá erro ao ler/gravar a coluna.)*
2. **Commit + push** (Render e Vercel fazem deploy do backend e frontend).
3. Na página **Família** → editar uma pessoa → **Escolher foto**.

> Ainda **não** há etiquetagem foto↔pessoa a partir deste ecrã (só escolha de
> avatar). A etiquetagem "quem aparece" continua na Biblioteca. Ver 2.10 para a
> melhoria sugerida.

---

## 5. Próximos passos sugeridos (por prioridade)

1. **Correr a migração 0009** no Supabase + deploy (desbloqueia a feature nova).
2. **Eliminar o grafo em disco** (2.1) — torna `get_person`/`get_graph` DB-backed
   e remove o JSON efémero. É o bug de produção mais real que resta.
3. **Decidir os testes** (2.3): arranjar a suite ou corrigir o relatório.
4. **Honestidade no relatório** sobre RAG/ChromaDB (2.4) e modos de execução (2.5).
5. **Limpar `photo_media_id` no `delete_media`** (2.9).
6. **Refactor incremental do frontend** (secção 3) — sem pressa, ficheiro a ficheiro.

> Nada na secção 2 ALTO/MÉDIO é difícil de corrigir; são sobretudo
> consequências do disco efémero do Render e de modelos Gemini que mudaram.
> Posso tratar de qualquer um destes a seguir — diz por onde queres começar.
