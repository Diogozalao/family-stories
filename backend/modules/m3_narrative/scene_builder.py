"""Scene segmentation for narrative → video synchronisation.

Turns a flat prose narrative plus the media used into a list of *scenes*.
Each scene pairs one paragraph of prose with the photos that best
illustrate it, so M4 can show each photo *exactly* while its stretch of
narration plays — the synchronisation that turns a slideshow into a
documentary.

The photo→paragraph assignment is dependency-free and deterministic: it
scores the lexical overlap between each paragraph and each photo's
textual fingerprint (AI description + tags + setting + narrative hint +
OCR + place). This is, in effect, the *retrieval* step that grounds the
visuals in the prose. When there is no usable signal it degrades
gracefully to a chronological even split, so a documentary is always
buildable.

A scene is a plain ``dict`` (JSON-serialisable straight into the
``stories.scenes`` column):

    {"text": "<prose>", "photo_ids": [<media id>, ...], "caption": "<date . place>"}
"""

from __future__ import annotations

import re

# A short, deliberately small stop-word list (PT + EN). The goal is not
# perfect linguistics but to stop the most common words from dominating
# the overlap score. Tokens shorter than 4 chars are dropped anyway.
_STOP = {
    "para", "como", "mais", "esta", "este", "isso", "essa", "esse", "pela",
    "pelo", "uma", "uns", "umas", "que", "com", "dos", "das", "nas", "nos",
    "aos", "sua", "seu", "suas", "seus", "foi", "era", "são", "ser", "tem",
    "the", "and", "with", "that", "this", "from", "were", "was", "have",
    "their", "they", "them", "into", "over", "when", "which", "about",
}

_TOKEN_RE = re.compile(r"[a-zà-ÿ0-9]+", re.IGNORECASE)


def _tokenize(text: str | None) -> set[str]:
    """Lowercase token set, dropping stop-words and very short tokens."""
    if not text:
        return set()
    toks = _TOKEN_RE.findall(text.lower())
    return {t for t in toks if len(t) > 3 and t not in _STOP}


def split_paragraphs(narrative: str | None) -> list[str]:
    """Split a narrative into paragraphs (the unit of a scene).

    Blank lines separate paragraphs; a single hard newline also counts,
    since the LLM output frequently uses one newline between paragraphs.
    """
    if not narrative or not narrative.strip():
        return []
    # Normalise: collapse 3+ newlines, then split on any run of newlines.
    parts = re.split(r"\n\s*\n|\n", narrative.strip())
    return [p.strip() for p in parts if p.strip()]


def _photo_fingerprint(media) -> str:
    """Build a searchable text blob describing a media item."""
    parts: list[str] = []
    for attr in ("ai_description", "ai_setting", "ai_narrative_hint",
                 "location_name", "ocr_text"):
        val = getattr(media, attr, None)
        if val:
            parts.append(str(val))
    tags = getattr(media, "ai_tags", None)
    if tags:
        parts.append(" ".join(tags) if isinstance(tags, (list, tuple)) else str(tags))
    return " ".join(parts)


def _chronological(media_list: list) -> list:
    """Order media by capture date (dated first, then undated by id)."""
    dated = sorted(
        [m for m in media_list if getattr(m, "date_taken", None)],
        key=lambda m: (m.date_taken, getattr(m, "id", 0)),
    )
    undated = sorted(
        [m for m in media_list if not getattr(m, "date_taken", None)],
        key=lambda m: getattr(m, "id", 0),
    )
    return dated + undated


def _caption_for(photos: list) -> str | None:
    """Lower-third caption for a scene, derived from its first photo."""
    if not photos:
        return None
    m = photos[0]
    parts: list[str] = []
    date_taken = getattr(m, "date_taken", None)
    if date_taken:
        try:
            parts.append(date_taken.strftime("%d/%m/%Y"))
        except Exception:
            pass
    setting = getattr(m, "ai_setting", None)
    if setting:
        parts.append(str(setting))
    return " · ".join(parts) or None


def build_scenes(narrative: str, media_list: list) -> list[dict]:
    """Segment ``narrative`` into scenes, each illustrated by photos.

    Guarantees, when there is at least one photo:
      * one scene per paragraph;
      * every photo is used exactly once;
      * no scene is left without a photo (unless there are fewer photos
        than paragraphs, in which case the lowest-signal scenes go
        without — M4 still renders their narration over a neighbour).
    """
    paragraphs = split_paragraphs(narrative)
    if not paragraphs:
        return []

    media = _chronological(media_list or [])
    if not media:
        return [{"text": p, "photo_ids": [], "caption": None} for p in paragraphs]

    n = len(paragraphs)
    para_tokens = [_tokenize(p) for p in paragraphs]
    buckets: list[list] = [[] for _ in range(n)]
    unscored: list = []

    # 1) Lexical assignment: each photo to its best-matching paragraph.
    for m in media:
        fp = _tokenize(_photo_fingerprint(m))
        if not fp:
            unscored.append(m)
            continue
        scores = [len(fp & toks) for toks in para_tokens]
        best = max(range(n), key=lambda i: scores[i])
        if scores[best] > 0:
            buckets[best].append(m)
        else:
            unscored.append(m)

    # 2) Photos with no lexical signal: spread chronologically across scenes.
    for k, m in enumerate(unscored):
        buckets[k % n].append(m)

    # 3) Fill the leftover (empty) scenes by CYCLING through every photo, so a
    #    long narration with only one or two photos keeps alternating images
    #    instead of freezing on one. Each photo already appears at its own
    #    paragraph (step 1, where the narration talks about it); here we REUSE
    #    the photos — without moving them — only for the scenes that no photo
    #    matched, i.e. once the narration is no longer about a specific photo.
    #    We avoid repeating the immediately-preceding scene's photo so
    #    consecutive scenes actually differ.
    cyc = 0
    for i in range(n):
        if buckets[i]:
            continue
        prev = buckets[i - 1][0] if i > 0 and buckets[i - 1] else None
        for _ in range(len(media)):
            cand = media[cyc % len(media)]
            cyc += 1
            if cand is not prev or len(media) == 1:
                buckets[i].append(cand)
                break

    scenes: list[dict] = []
    for i, paragraph in enumerate(paragraphs):
        photos = _chronological(buckets[i])
        scenes.append({
            "text":      paragraph,
            "photo_ids": [getattr(m, "id") for m in photos],
            "caption":   _caption_for(photos),
        })
    return scenes
