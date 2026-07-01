# Imagens necessárias para o relatório

Coloca todos os ficheiros na pasta `Projetos/images/`. Onde uma imagem
está em falta, o LaTeX mostra uma moldura **"[IMAGEM A INSERIR]"** com a
descrição — o documento compila à mesma. Para inserir a imagem real:
troca o comando `\figph{...}` pela linha `\includegraphics` que está
**comentada** logo acima dele em cada figura.

| # | Ficheiro sugerido | Onde (capítulo / figura) | O que deve mostrar | Como obter |
|---|---|---|---|---|
| 1 | `ubi-fe-di.png` | Capa | Logótipo oficial UBI · Faculdade de Engenharia · Departamento de Informática | Site/manual de identidade da UBI |


| 2 | `cronograma.png` | Cap.3 · Fig. cronograma | Diagrama de Gantt das fases F1–F6 | Ferramenta de gestão de projeto, draw.io ou TikZ |


| 3 | *(TikZ — já feito)* | Cap.5 · Arquitetura global | — | Já desenhado em TikZ no `cap5...tex` |


| 4 | `fullstack.png` | Cap.5 · Fig. full-stack | Diagrama vertical camada-a-camada (existe esboço no teu PDF de estudo) | Redesenhar o diagrama do estudo inicial |


| 5 | `casos_uso.png` | Cap.4 · Fig. casos de uso | Diagrama UML de casos de uso | draw.io ou PlantUML |


| 6 | `modelo_er.png` | Cap.5 · Fig. ER | Diagrama Entidade-Relação das tabelas | `eralchemy` a partir dos modelos SQLAlchemy, ou draw.io |
| 7 | `ui_dashboard.png` | Cap.5 · Fig. Dashboard | Captura de ecrã do Dashboard | Print do sistema a correr |
| 8 | `ui_library.png` | Cap.5 · Fig. Biblioteca | Captura da galeria/biblioteca | Print |
| 9 | `ui_generate.png` | Cap.5 · Fig. Gerar | Captura do assistente de geração | Print |
| 10 | `ui_reader.png` | Cap.5 · Fig. Leitor | Captura do leitor de histórias (drop-cap) | Print |
| 11 | `ui_videos.png` | Cap.5 · Fig. Vídeos | Captura da galeria de vídeos / player | Print |
| 12 | `frame_video.png` | Cap.6 · Fig. fotograma | Frame de um vídeo gerado (letterbox + legenda) | Exportar frame de um MP4 produzido pelo sistema |
| 13 | `pytest.png` | Cap.7 · Fig. pytest | Captura da execução `pytest -v` (37 testes OK) | Terminal |
| 14 | `grafo_familiar.png` *(opcional)* | (podes adicionar no Cap.6 M2) | Visualização do grafo NetworkX de uma família | `networkx` + matplotlib |

## Atualização 2026-06-19 — camada de IA com 3 níveis
- O **diagrama de arquitetura global** (Cap.5, TikZ) foi atualizado: a
  caixa **IA** passa a mostrar **Ollama (local) · Gemini (nuvem) · Groq
  (*fallback*)**, refletindo a nova cadeia de geração de texto. Como é
  TikZ, **não precisa de ficheiro de imagem** — recompila e fica certo.
- Se tiveres capturas de ecrã com a arquitetura/infra (não há nenhuma na
  lista abaixo), nenhuma precisa de ser refeita — a mudança é só no
  diagrama em código.
- Os *prints* de UI (#7–#11) **não** são afetados: o Groq é interno
  (*backend*) e não aparece na interface.

## Notas
- **Figuras já resolvidas em TikZ** (não precisam de imagem): o diagrama
  de **arquitetura global** (Cap.5) está desenhado em código (já inclui
  a camada de IA de 3 níveis acima descrita).
- Para as capturas de ecrã, usa preferencialmente o **tema claro** e
  resolução alta (retina) para boa qualidade na impressão.
- Se quiseres, o diagrama **full-stack** (#4) também pode ser refeito em
  TikZ para ficar vetorial — diz-me e eu faço.
- O logótipo (#1): se não tiveres o PNG oficial, posso deixar a capa só
  com texto (sem moldura) — basta dizeres.
