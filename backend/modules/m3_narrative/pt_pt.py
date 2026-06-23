"""Deterministic European-Portuguese (pt-PT) post-processing for narratives.

The prompts already *instruct* the LLM to write in European Portuguese, but
Llama 3.x and Gemini Flash both drift back to Brazilian Portuguese — the most
common complaint about the generated stories. Instruction alone is not
reliable, so this module adds a deterministic safety net that runs **after**
generation and mechanically corrects the highest-frequency brasileirismos.

Two public helpers:

* :func:`pt_pt_postprocess` — returns the corrected text plus how many
  substitutions were made (for logging / the evaluation harness).
* :func:`count_brasileirismos` — a read-only counter used as an objective
  quality metric (see the evaluation script and the report's cap.7 grid).

The corrections are intentionally conservative: only unambiguous vocabulary
swaps and the ``auxiliar + gerúndio`` → ``auxiliar + a + infinitivo``
construction, which is the single most recognisable BR/PT grammatical tell.
Pronoun rewrites (``você`` → ``tu``) are *not* applied automatically because
they cascade into verb agreement; ``você`` is only *counted* as a tell.
"""

from __future__ import annotations

import re

# ── Vocabulary: Brazilian → European, unambiguous and common ───────────────
# Keep multi-word entries before their single-word components so they win.
#
# IMPORTANT: only include swaps that keep the same grammatical gender/number,
# so we never produce an article mismatch ("na passeio"). Gender-flipping or
# semantically ambiguous words (calçada→passeio, geladeira→frigorífico,
# banheiro→casa de banho, grama, time…) are deliberately left out.
BR_TO_PT: dict[str, str] = {
    "café da manhã": "pequeno-almoço",
    "ônibus": "autocarro",
    "trem": "comboio",
    "celular": "telemóvel",
    "câmera": "câmara",
    "sorvete": "gelado",
    "suco": "sumo",
    "xícara": "chávena",
    "esporte": "desporto",
    "esportes": "desportos",
    "açougue": "talho",
    "cotidiano": "quotidiano",
    "registro": "registo",
    "registros": "registos",
    "terno": "fato",
    "garoto": "miúdo",
    "garota": "miúda",
    "garotos": "miúdos",
    "garotas": "miúdas",
    "moça": "rapariga",
    "moças": "raparigas",
    "moço": "rapaz",
    "vovô": "avô",
    "vovó": "avó",
    "mamãe": "mãe",
    "papai": "pai",
    "aterrissar": "aterrar",
    "bonde": "elétrico",
    "trilho": "carril",
}

# Auxiliaries that, followed by a gerund, mark the BR continuous tense. The
# pt-PT form is "auxiliar + a + infinitivo" ("estava a chorar").
_AUX = (
    r"est(?:ou|ás|á|amos|ão|ava|avas|ávamos|avam)"
    r"|continu(?:o|as|a|amos|am|ava|avam)"
    r"|fic(?:o|as|a|amos|am|ava|avam|ou|aram)"
    r"|and(?:o|as|a|amos|am|ava|avam)"
    r"|vinha|vinham|ia|iam|seg(?:ue|uia|uiam)|permanec(?:e|ia|iam)"
)
_GERUND_RE = re.compile(
    rf"\b({_AUX})\s+(\w*?)(ando|endo|indo)\b",
    re.IGNORECASE,
)
_INF = {"ando": "ar", "endo": "er", "indo": "ir"}

_VOCAB_RES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"\b{re.escape(br)}\b", re.IGNORECASE), pt)
    for br, pt in BR_TO_PT.items()
]

_YOU_RE = re.compile(r"\bvoc[êe]s?\b", re.IGNORECASE)


def _match_case(src: str, repl: str) -> str:
    """Carry ``src``'s capitalisation onto ``repl`` (Title or lower)."""
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def _fix_gerund(m: re.Match[str]) -> str:
    aux, stem, end = m.group(1), m.group(2), m.group(3)
    if not stem:                       # bare "indo"/"endo" — leave it alone
        return m.group(0)
    return f"{aux} a {stem}{_INF[end.lower()]}"


def pt_pt_postprocess(text: str) -> tuple[str, int]:
    """Correct the common brasileirismos in ``text``.

    Returns ``(corrected_text, n_substitutions)``.
    """
    if not text:
        return text, 0

    count = 0

    def _vocab_sub(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return _match_case(m.group(0), repl)

    for pattern, repl in _VOCAB_RES:
        text = pattern.sub(_vocab_sub, text)

    def _gerund_sub(m: re.Match[str]) -> str:
        nonlocal count
        fixed = _fix_gerund(m)
        if fixed != m.group(0):
            count += 1
        return fixed

    text = _GERUND_RE.sub(_gerund_sub, text)
    return text, count


def count_brasileirismos(text: str) -> int:
    """Read-only count of BR tells: vocabulary + gerund + ``você`` forms.

    Used as an objective pt-PT adherence metric. Does not mutate the text.
    """
    if not text:
        return 0
    n = 0
    for pattern, _ in _VOCAB_RES:
        n += len(pattern.findall(text))
    for m in _GERUND_RE.finditer(text):
        if m.group(2):                 # skip bare "indo"
            n += 1
    n += len(_YOU_RE.findall(text))
    return n
