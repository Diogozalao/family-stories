# Changelog do Relatório (Projetos/)

Histórico de alterações ao relatório LaTeX. Cada entrada indica **ficheiro
+ secção + natureza da mudança**, para refletir manualmente no Overleaf.

> Os commits são sempre feitos pelo Diogo. Este ficheiro é apenas um
> registo de apoio — eu (assistente) edito e aviso; o `git` fica do teu lado.

Formato: `AAAA-MM-DD` · `[Adição|Correção|Reescrita|Remoção]` · ficheiro · descrição.

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
