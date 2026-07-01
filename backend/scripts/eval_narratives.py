"""Avaliação experimental da geração narrativa (M3).

Gera narrativas para os ficheiros GEDCOM de exemplo (``data/samples/gedcom``),
variando o *template* e a intenção do utilizador, e mede um conjunto de
métricas objetivas por geração. Materializa os entregáveis pedidos no
enunciado (T4/T5/T6): conjunto de casos de teste, dados brutos e comparação
entre estruturas narrativas/prompts.

Métricas por geração:
  * backend de LLM usado (ollama / gemini / groq)
  * sucesso/falha + tempo de geração (s)
  * extensão (palavras, parágrafos)
  * aderência pt-PT: brasileirismos detetados antes/depois do pós-processamento
    e nº de correções aplicadas (ver ``m3_narrative.pt_pt``)
  * originalidade: nº de clichés (de uma lista negra) presentes no texto

Saída:
  * ``data/eval/eval_results.csv``  — dados brutos (uma linha por geração)
  * ``data/eval/narratives/*.txt``  — cada narrativa gerada
  * tabela-resumo impressa no terminal (média por template)

Uso::

    venv/bin/python -m backend.scripts.eval_narratives                # corre tudo
    venv/bin/python -m backend.scripts.eval_narratives --limit 3      # só 3 gerações
    venv/bin/python -m backend.scripts.eval_narratives --templates default,viagem
    venv/bin/python -m backend.scripts.eval_narratives --dry-run      # sem LLM (valida o pipeline/métricas)
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from backend.modules.m1_ingestion.gedcom_parser import GEDCOMParser     # noqa: E402
from backend.modules.m2_temporal.family_graph import FamilyGraph        # noqa: E402
from backend.modules.m3_narrative.pt_pt import (                        # noqa: E402
    count_brasileirismos,
    pt_pt_postprocess,
)
from backend.modules.m3_narrative.templates import (                    # noqa: E402
    GROUNDING_RULES,
    ORIGINALITY_RULES,
    get_template,
)

SAMPLES_DIR = ROOT / "data" / "samples" / "gedcom"
OUT_DIR     = ROOT / "data" / "eval"

# Intenções (user_focus) testadas por família — variar o ângulo é o cerne de T5.
FOCUSES = [
    "a história e as origens desta família ao longo das gerações",
    "uma reunião de família num verão memorável",
]

# Lista negra de clichés para a métrica de originalidade.
CLICHES = [
    "cheiro a pão", "pão acabado de cozer", "molduras de cartão",
    "cor de cobre", "sol dourado", "o tempo parou", "como se fosse ontem",
    "para sempre no coração", "memórias preciosas", "uma lágrima",
    "era uma vez", "tudo começou",
]

# Texto canónico (propositadamente "brasileiro") para o modo --dry-run: não
# chama o LLM, mas exercita as métricas e o pós-processamento ponta-a-ponta.
_DRY_TEXT = (
    "A vovó estava chorando quando o trem chegou à estação. O papai pegou o "
    "celular e tirou uma foto enquanto o garoto continuava sorrindo. "
    "Foi como se o tempo parou, uma memória preciosa guardada para sempre no "
    "coração.\n\nNaquela manhã tomaram café da manhã juntos antes da viagem."
)


def _graph_and_events(parsed: dict) -> tuple[FamilyGraph, str]:
    """Constrói um FamilyGraph em memória + um events_context a partir do GEDCOM."""
    class _P:
        __slots__ = ("id", "name", "birth_date", "birth_place", "gedcom_id", "notes")

        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    local_to_id: dict[str, int] = {}
    graph = FamilyGraph()
    for i, (local_id, indi) in enumerate(parsed["individuals"].items(), start=1):
        if not indi.get("name"):
            continue
        local_to_id[local_id] = i
        graph.add_person(_P(
            id=i,
            name=indi["name"],
            birth_date=indi.get("birth_date"),
            birth_place=indi.get("birth_place"),
            gedcom_id=indi.get("gedcom_id"),
            notes=" ".join(indi.get("notes", [])) or None,
        ))

    events: list[str] = []
    for fam in parsed["families"].values():
        h = local_to_id.get(fam.get("husband"))
        w = local_to_id.get(fam.get("wife"))
        if h and w:
            graph.add_relation(h, w, "cônjuge")
            graph.add_relation(w, h, "cônjuge")
            if fam.get("marr_date"):
                place = fam.get("marr_place") or "local desconhecido"
                events.append(f"Casamento em {place} em {fam['marr_date'].year}.")
        for child_local in fam.get("children", []):
            c = local_to_id.get(child_local)
            if not c:
                continue
            if h:
                graph.add_relation(h, c, "pai")
                graph.add_relation(c, h, "filho de")
            if w:
                graph.add_relation(w, c, "mãe")
                graph.add_relation(c, w, "filho de")

    for indi in parsed["individuals"].values():
        if indi.get("name") and indi.get("birth_date"):
            place = indi.get("birth_place") or "local desconhecido"
            events.append(f"{indi['name']} nasceu em {place} em {indi['birth_date'].year}.")

    events_context = "\n".join(f"[Momento {i}] {e}" for i, e in enumerate(events, 1))
    return graph, events_context or "Sem factos disponíveis."


def _build_prompt(event_type: str, family_context: str, events_context: str, focus: str) -> str:
    """Replica a montagem do prompt do generator.py (sem a parte de BD/RAG)."""
    template = get_template(event_type)
    prompt = template["prompt"].format(
        tone=template["tone"],
        structure=template["structure"],
        family_context=family_context,
        events_context=events_context,
        user_focus=focus,
    )
    prompt += "\n\n" + GROUNDING_RULES
    prompt += "\n\n" + ORIGINALITY_RULES
    prompt += "\n\nIMPORTANTE: Escreve a narrativa inteira em português europeu (pt-PT)."
    return prompt


def _cliche_hits(text: str) -> int:
    low = text.lower()
    return sum(1 for c in CLICHES if c in low)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--templates", default="default,fotografia,viagem,celebração",
                    help="lista separada por vírgulas de event_types a testar")
    ap.add_argument("--limit", type=int, default=0, help="máx. de gerações (0 = todas)")
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--dry-run", action="store_true",
                    help="não chama o LLM; usa um texto canónico p/ validar as métricas")
    args = ap.parse_args()

    templates = [t.strip() for t in args.templates.split(",") if t.strip()]
    ged_files = sorted(SAMPLES_DIR.glob("*.ged"))
    if not ged_files:
        print(f"Sem ficheiros GEDCOM em {SAMPLES_DIR}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "narratives").mkdir(exist_ok=True)

    llm = None
    if not args.dry_run:
        from backend.modules.m3_narrative.llm_client import LLMClient
        llm = LLMClient()
        print(f"Backend de LLM: {llm.backend}\n")

    rows: list[dict] = []
    n = 0
    for ged in ged_files:
        parsed = GEDCOMParser().parse(ged)
        if not parsed["individuals"]:
            continue
        graph, events_context = _graph_and_events(parsed)
        family_context = "Relações familiares conhecidas: " + graph.get_narrative_summary()

        for event_type in templates:
            for focus in FOCUSES:
                if args.limit and n >= args.limit:
                    break
                n += 1
                prompt = _build_prompt(event_type, family_context, events_context, focus)

                t0 = time.perf_counter()
                ok, err, raw = True, "", ""
                try:
                    if args.dry_run:
                        raw = _DRY_TEXT
                    else:
                        raw = llm.generate(prompt, args.max_tokens)
                except Exception as exc:                       # noqa: BLE001
                    ok, err = False, str(exc)[:200]
                secs = round(time.perf_counter() - t0, 2)

                br_before = count_brasileirismos(raw) if raw else 0
                final, fixes = pt_pt_postprocess(raw) if raw else ("", 0)
                br_after = count_brasileirismos(final) if final else 0

                row = {
                    "family":     ged.stem,
                    "template":   event_type,
                    "focus":      focus[:40],
                    "backend":    (llm.backend if llm else "dry-run"),
                    "ok":         ok,
                    "seconds":    secs,
                    "words":      len(final.split()),
                    "paragraphs": len([p for p in final.split("\n\n") if p.strip()]),
                    "br_before":  br_before,
                    "br_after":   br_after,
                    "pt_fixes":   fixes,
                    "cliches":    _cliche_hits(final),
                    "error":      err,
                }
                rows.append(row)
                status = "ok" if ok else f"FALHOU ({err[:60]})"
                print(f"[{n:02d}] {ged.stem:12s} · {event_type:12s} · {secs:5.1f}s · "
                      f"BR {br_before}->{br_after} · {row['words']:3d} palavras · {status}")

                if final:
                    safe = f"{ged.stem}_{event_type}_{n}.txt".replace("ç", "c")
                    (OUT_DIR / "narratives" / safe).write_text(final, encoding="utf-8")
            if args.limit and n >= args.limit:
                break
        if args.limit and n >= args.limit:
            break

    # ── Escrita do CSV ────────────────────────────────────────────────────
    csv_path = OUT_DIR / "eval_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # ── Resumo por template ───────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("RESUMO POR TEMPLATE (médias)")
    print("=" * 72)
    print(f"{'template':14s} {'n':>3s} {'ok%':>5s} {'seg':>6s} {'palavras':>9s} "
          f"{'BR_antes':>9s} {'BR_depois':>10s} {'cliches':>8s}")
    by_t: dict[str, list[dict]] = {}
    for r in rows:
        by_t.setdefault(r["template"], []).append(r)

    def _avg(xs):
        return round(statistics.mean(xs), 1) if xs else 0.0

    for t, rs in by_t.items():
        oks = [r for r in rs if r["ok"]]
        print(f"{t:14s} {len(rs):>3d} {100*len(oks)//len(rs):>4d}% "
              f"{_avg([r['seconds'] for r in oks]):>6} "
              f"{_avg([r['words'] for r in oks]):>9} "
              f"{_avg([r['br_before'] for r in oks]):>9} "
              f"{_avg([r['br_after'] for r in oks]):>10} "
              f"{_avg([r['cliches'] for r in oks]):>8}")

    total_ok = sum(1 for r in rows if r["ok"])
    print("-" * 72)
    print(f"TOTAL: {len(rows)} gerações · {total_ok} ok · "
          f"BR médio {_avg([r['br_before'] for r in rows])} -> "
          f"{_avg([r['br_after'] for r in rows])} após pós-processamento")
    print(f"\nDados brutos:  {csv_path}")
    print(f"Narrativas:    {OUT_DIR / 'narratives'}")


if __name__ == "__main__":
    main()
