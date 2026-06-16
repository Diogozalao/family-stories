# Changelog do Relatório (Projetos/)

Histórico de alterações ao relatório LaTeX. Cada entrada indica **ficheiro
+ secção + natureza da mudança**, para refletir manualmente no Overleaf.

> Os commits são sempre feitos pelo Diogo. Este ficheiro é apenas um
> registo de apoio — eu (assistente) edito e aviso; o `git` fica do teu lado.

Formato: `AAAA-MM-DD` · `[Adição|Correção|Reescrita|Remoção]` · ficheiro · descrição.

---

## 2026-06-15 — Projetos isolados (timeline/família por projeto + upload)

- **[Adição]** `cap5_arquitetura_design.tex` · modelo de dados — nota de
  que cada `Project` é um espaço isolado (fotos, timeline derivada das suas
  fotos, família por etiqueta do projeto, histórias e vídeos próprios).

> Frontend: a Linha Temporal do projeto passa a ser construída só a partir
> das fotos do projeto; a Família do projeto fica isolada (etiqueta = nome
> do projeto) com toggle árvore/lista + editor + import GEDCOM; e o
> "Adicionar fotos" passa a permitir carregar foto nova OU escolher da
> Biblioteca. Sem migração de BD. tsc OK.

---

## 2026-06-16 — Tarefas isoladas por projeto

- **[Adição]** `cap5_arquitetura_design.tex` · modelo de dados —
  `TaskRecord` ganha `project_id`; as tarefas em segundo plano de um
  projeto deixam de se misturar com as dos outros (filtragem por projeto
  na página de Tarefas).

> Backend: `task_records.project_id` (FK → projects, ON DELETE SET NULL);
> definido ao criar a tarefa (narrativa = projeto do pedido; vídeo =
> projeto da história); `GET /tasks?project_id=` filtra. Frontend: chips de
> filtro por projeto + etiqueta de projeto em cada tarefa. Migração de BD:
> `0008_task_project.sql`. tsc OK.

---

## 2026-06-16 — Fotos↔pessoas (etiquetagem) ligadas à narrativa

- **[Adição]** `cap5_arquitetura_design.tex` — `MediaFile` ganha
  `person_ids` (pessoas etiquetadas na foto).
- **[Adição]** `cap6_implementacao.tex` · §M2/M3 — etiquetagem de pessoas
  por fotografia; os nomes («quem aparece») entram no contexto do M3,
  ligando rostos a nomes na narrativa.

> Código implementado e testado (36 testes; tsc OK). Migração de BD:
> `0007_media_persons.sql`.

---

## 2026-06-16 — Árvore: exportação GEDCOM + descrições na narrativa

- **[Reescrita]** `cap6_implementacao.tex` · §M2 — editor com todas as
  relações (pai/mãe/filho/irmão/cônjuge); **descrições (notas) de cada
  pessoa entram no contexto do M3**; **exportação para GEDCOM 5.5.1**
  (inverso do parser, re-importável → interoperabilidade).

> Código implementado e testado (conversor GEDCOM validado; 36 testes; tsc OK).

---

## 2026-06-15 — Árvore familiar: relações na BD, vista interativa e editor

- **[Adição]** `cap5_arquitetura_design.tex` · modelo de dados — nova
  entidade `Relationship` (relações na BD, já não em JSON efémero) e
  campo `sexo` em `Person`.
- **[Reescrita]** `cap6_implementacao.tex` · §M2 — relações persistidas na
  tabela `relationships`; nova vista interativa da árvore (React Flow) e
  editor manual (pessoas/relações + assistente de pedigree), com o grafo
  do M3 reconstruído a partir da BD após cada edição.

> Reflete código já implementado e testado (backend: 36 testes; frontend:
> tsc OK). Migração de BD necessária: `0005_relationships.sql` (+ `0004`).

---

## 2026-06-13 — Verificação geral + aprofundamento (Cap. 3, 5, 6)

**Correções factuais (todos os capítulos):**
- **Resumo** — acrescentada a segmentação em cenas (sincronização imagem↔narração).
- **Cap. 1** — duas novas contribuições: narrativa em cenas e geração assíncrona/resiliência a cold-starts.
- **Cap. 7** — nº de testes corrigido (36 unitários a passar; removido `test_security` desatualizado, adicionado `test_scene_builder`); legenda da figura e secção de bugs atualizadas (fix `UTC` no date_resolver, resiliência a cold-start).
- **Cap. 8** — síntese passa a referir cenas + assíncrono in-process; limitações atualizadas (RAG já ligado mas stub na nuvem; deriva de sincronização); removido o "rebaixamento síncrono" agora obsoleto.

**Reescrita aprofundada:**
- **Cap. 3** — tabela comparativa de decisões (alternativas + razão); nova subsecção "Tarefas assíncronas: Celery vs. in-process"; nova subsecção "Princípios de engenharia transversais"; RAG com retrieval ligado.
- **Cap. 5** — visão global atualizada (duas vias de execução); nova secção "Fluxo de Dados e Execução" (tabela consome/produz + sequência de geração assíncrona); tabela de relações entre entidades.
- **Cap. 6** — M2 com profundidade (qualificadores GEDCOM, validação de datas, eventos de casamento); excerto do executor in-process (`lst:inproc`); nova subsecção "Resiliência a cold starts".

> Nota: a lista de acrónimos existe **uma única vez** (`acronimos.tex`, incluída 1× em `main.tex`). Se aparecerem duas no Overleaf, é uma cópia extra a remover lá.

---

## 2026-06-11 — M1: análise de IA diferida (upload não bloqueia)

- **[Reescrita]** `cap6_implementacao.tex` · §M1 — nova ordem do pipeline
  (security → EXIF → Storage → IA) e novo parágrafo *"Análise diferida"*:
  a parte lenta (Gemini/OCR) passa para segundo plano via executor
  in-process; a foto fica logo visível e a descrição preenche-se depois.

> Reflete código já implementado e testado (36 testes unitários a passar).
> Sem migração de BD. Frontend: polling da biblioteca + indicador "a analisar".

---

## 2026-06-11 — Geração assíncrona in-process (sem Celery na nuvem)

- **[Reescrita]** `cap6_implementacao.tex` · §"Fila de tarefas e sweep de
  órfãs" — passa a descrever as duas vias de execução em segundo plano
  (Celery+Redis OU executor *in-process* num thread pool quando
  `CELERY_ENABLED=False`), em vez do antigo "rebaixamento para síncrono".

> Reflete código já implementado e testado (36 testes unitários a passar).
> Sem migração de BD. Frontend já preparado (polling de /tasks).

---

## 2026-06-11 — Pipeline por cenas (narrativa↔vídeo sincronizados)

- **[Reescrita]** `cap6_implementacao.tex` · §M3 (RAG) — passa a descrever
  o *retrieval* efetivamente ligado à geração (seleção do subconjunto de
  fotos relevantes via `search_media_ids`).
- **[Adição]** `cap6_implementacao.tex` · nova subsecção *"Segmentação em
  cenas"* (M3) + excerto `lst:scene` com a forma de uma cena.
- **[Reescrita]** `cap6_implementacao.tex` · §M4 *"Narração e sincronização
  áudio-vídeo por cena"* — modo documentário (`build_documentary`), TTS por
  cena + novo excerto `lst:plandur` (`plan_scene_durations`).
- **[Adição]** `cap5_arquitetura_design.tex` · modelo de dados — campo
  `scenes` (JSON) na entidade `Story`.

> Nota: estas mudanças refletem código já implementado e testado
> (7 testes novos em `test_scene_builder.py`, 36 testes unitários a passar).
> Migração de BD necessária: `backend/sql/0004_story_scenes.sql`.

---

## 2026-06-11 — Criação inicial do relatório

- **[Adição]** `main.tex` — documento mestre: pacotes, estilos, índices
  (geral, figuras, tabelas, excertos de código, acrónimos), `\input` dos
  capítulos, bibliografia (BibTeX, estilo IEEE) e apêndices.
- **[Adição]** `capa.tex` — capa estilo UBI/FE; Projeto Final de
  Licenciatura; autor Diogo Dinis (nº 52374); orientadores Vasco Lopes e
  João Dias; placeholder do logótipo FE-UBI.
- **[Adição]** `resumo.tex` — Resumo + Abstract + palavras-chave.
- **[Adição]** `agradecimentos.tex` — agradecimentos.
- **[Adição]** `acronimos.tex` — lista de acrónimos.
- **[Adição]** `cap1_introducao.tex` — contexto, problema, objetivos,
  âmbito, contribuições, estrutura.
- **[Adição]** `cap2_estado_da_arte.tex` — soluções existentes (Big Four,
  MyHeritage, Google Photos) e enquadramento teórico (LLM, MLLM, RAG,
  paradigmas, desafios, vídeo, TTS), com base no estudo inicial.
- **[Adição]** `cap3_metodologia_tecnologias.tex` — metodologia ágil,
  fases F1–F6, stack tecnológica justificada.
- **[Adição]** `cap4_requisitos.tex` — RF/RNF (MoSCoW), casos de uso,
  user stories.
- **[Adição]** `cap5_arquitetura_design.tex` — arquitetura global (TikZ),
  evolução local-first → multi-tenant, modelo de dados, UI/UX.
- **[Adição]** `cap6_implementacao.tex` — implementação M1–M4, backend,
  frontend, segurança, deployment; 6 excertos de código reais.
- **[Adição]** `cap7_testes_validacao.tex` — plano de testes, 37 testes
  pytest, métricas de qualidade narrativa.
- **[Adição]** `cap8_conclusoes.tex` — síntese, limitações, trabalho futuro.
- **[Adição]** `apendices.tex` — endpoints da API, configuração de deploy.
- **[Adição]** `referencias.bib` — referências BibTeX (estilo IEEE).
- **[Adição]** `IMAGENS_NECESSARIAS.md` — lista das imagens a inserir.
