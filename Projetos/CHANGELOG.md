# Changelog do Relatório (Projetos/)

Histórico de alterações ao relatório LaTeX. Cada entrada indica **ficheiro
+ secção + natureza da mudança**, para refletir manualmente no Overleaf.

> Os commits são sempre feitos pelo Diogo. Este ficheiro é apenas um
> registo de apoio — eu (assistente) edito e aviso; o `git` fica do teu lado.

Formato: `AAAA-MM-DD` · `[Adição|Correção|Reescrita|Remoção]` · ficheiro · descrição.

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
