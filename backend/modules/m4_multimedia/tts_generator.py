"""Text-to-speech narration generation.

Primary backend: ``edge-tts`` — Microsoft Edge's online neural voices.
Two languages are supported, picked by the ``language`` constructor
argument so the video matches the UI toggle:

  * ``pt`` (default) — Duarte, Raquel, Fernanda (European Portuguese)
  * ``en``           — Ryan (en-GB), Sonia (en-GB), Guy (en-US)

Fallback: ``gTTS`` — kept as a fail-safe for runs without network or
when the Edge endpoint refuses the request. ``gTTS`` accepts the same
two letter codes (``pt``, ``en``), so the same ``language`` argument
threads through both backends.

The public ``TTSGenerator.generate()`` API is unchanged (synchronous,
writes an MP3, returns the duration) so the M4 processor doesn't have
to know which backend produced the audio.
"""

import asyncio
from pathlib import Path

import structlog

log = structlog.get_logger()


# Neural voice catalogue, keyed by ``language``. Each language picks
# a "default" voice the caller gets when no specific voice is asked for.
EDGE_VOICES: dict[str, dict[str, str]] = {
    "pt": {
        "default": "pt-PT-DuarteNeural",    # memoir-friendly male
        "female":  "pt-PT-RaquelNeural",
        "warm":    "pt-PT-FernandaNeural",
    },
    "en": {
        "default": "en-GB-RyanNeural",      # warm British male
        "female":  "en-GB-SoniaNeural",
        "us":      "en-US-GuyNeural",
    },
}


def _resolve_voice(language: str, voice: str | None) -> str:
    """Map a requested voice to a concrete neural voice id.

    ``voice`` may be a gender the user picked in the wizard
    (``"male"``/``"female"`` — also accepts the PT words) or an explicit
    Edge voice id. ``None`` → the language's default (male). This is what
    lets the user choose a masculine or feminine narrator per story.
    """
    voices = EDGE_VOICES.get(language) or EDGE_VOICES["pt"]
    if not voice:
        return voices["default"]
    v = voice.strip().lower()
    if v in ("male", "m", "masculina", "masculino", "homem", "default"):
        return voices["default"]
    if v in ("female", "f", "feminina", "feminino", "mulher"):
        return voices.get("female", voices["default"])
    return voice                      # already an explicit Edge voice id


def _pick_default_voice(language: str) -> str:
    return _resolve_voice(language, None)


def _gtts_params_for(language: str) -> tuple[str, str]:
    """Return ``(lang, tld)`` for gTTS that yields the most natural variant."""
    if language == "en":
        return ("en", "co.uk")   # en-GB sounds closer to our Edge voice
    return ("pt", "pt")           # pt-PT (avoid Brazilian)


class TTSGenerator:
    """Synthesise narration MP3s, preferring neural voices over gTTS."""

    def __init__(
        self,
        language: str = "pt",
        voice:    str | None = None,
    ):
        self.language = language if language in EDGE_VOICES else "pt"
        # ``voice`` accepts a gender ("male"/"female") or an explicit voice id.
        self.voice    = _resolve_voice(self.language, voice)
        # ``lang``/``tld`` are kept for the gTTS fallback only.
        self.lang, self.tld = _gtts_params_for(self.language)

    # ── Public API ────────────────────────────────────────────

    def generate(self, text: str, output_path: Path) -> float:
        """Synthesize ``text`` into an MP3 at ``output_path``.

        Tries ``edge-tts`` first; if it raises for any reason (no network,
        rate limit, etc.) we fall back to ``gTTS`` so a documentary still
        gets *some* audio.
        """
        try:
            self._render_edge_tts(text, output_path)
            log.info("tts_generated", backend="edge-tts", voice=self.voice,
                     path=str(output_path), chars=len(text))
        except Exception as exc:
            log.warning("tts_edge_failed_fallback_gtts", error=str(exc))
            self._render_gtts(text, output_path)
            log.info("tts_generated", backend="gtts",
                     path=str(output_path), chars=len(text))
        return self._get_duration(output_path)

    def generate_with_marks(self, text: str, output_path: Path) -> tuple[float, list[dict]]:
        """Like :meth:`generate` but also returns word-level timestamps.

        Returns ``(duration_seconds, marks)`` where each mark is
        ``{"start", "end", "word"}`` (seconds, in this clip's own timeline).
        edge-tts emits these as ``WordBoundary`` events; the gTTS fallback has
        none (empty list) and the caller then times subtitles by proportion.
        """
        try:
            marks = self._render_edge_tts_with_marks(text, output_path)
            log.info("tts_generated", backend="edge-tts", voice=self.voice,
                     path=str(output_path), chars=len(text), marks=len(marks))
        except Exception as exc:                       # noqa: BLE001
            log.warning("tts_edge_failed_fallback_gtts", error=str(exc))
            self._render_gtts(text, output_path)
            marks = []
        return self._get_duration(output_path), marks

    def _render_edge_tts_with_marks(self, text: str, output_path: Path) -> list[dict]:
        """edge-tts streaming: write the MP3 *and* collect word boundaries."""
        import edge_tts
        marks: list[dict] = []

        async def _run() -> None:
            comm = edge_tts.Communicate(text=text, voice=self.voice,
                                        rate="-6%", pitch="-2Hz",
                                        boundary="WordBoundary")
            with open(output_path, "wb") as fh:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        fh.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start = chunk["offset"] / 1e7      # 100-ns ticks → seconds
                        end   = start + chunk["duration"] / 1e7
                        marks.append({"start": start, "end": end, "word": chunk["text"]})

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
        return marks

    def generate_paragraphs(self, text: str, output_dir: Path) -> list[dict]:
        """One MP3 per paragraph. Returns ``[{path, duration, text}]``."""
        output_dir.mkdir(parents=True, exist_ok=True)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()] or [text.strip()]

        results: list[dict] = []
        for index, paragraph in enumerate(paragraphs):
            if not paragraph:
                continue
            out = output_dir / f"para_{index:02d}.mp3"
            try:
                duration = self.generate(paragraph, out)
                results.append({"path": out, "duration": duration, "text": paragraph})
                log.info("tts_paragraph", index=index, duration=round(duration, 1))
            except Exception as exc:
                log.warning("tts_paragraph_skip", index=index, error=str(exc))
        return results

    # ── Backends ──────────────────────────────────────────────

    def _render_edge_tts(self, text: str, output_path: Path) -> None:
        """Use ``edge-tts`` to synthesise ``text`` into ``output_path``.

        We tweak ``rate`` and ``pitch`` very slightly: a touch slower than
        default and a hair lower in pitch reads more naturally for a memoir
        narration, sounds less like a news anchor.
        """
        import edge_tts

        async def _run() -> None:
            comm = edge_tts.Communicate(
                text   = text,
                voice  = self.voice,
                rate   = "-6%",     # 6% slower for memoir-style pacing
                pitch  = "-2Hz",    # slightly lower for warmer tone
            )
            await comm.save(str(output_path))

        # The M4 pipeline calls us synchronously from a thread executor;
        # spin up an isolated loop here so we don't collide with FastAPI's.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    def _render_gtts(self, text: str, output_path: Path) -> None:
        """Fallback: Google's gTTS robot."""
        from gtts import gTTS
        tts = gTTS(text=text, lang=self.lang, tld=self.tld, slow=False)
        tts.save(str(output_path))

    # ── Helpers ───────────────────────────────────────────────

    def _get_duration(self, path: Path) -> float:
        """Read the duration of an MP3 without loading the full file."""
        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(str(path))
            duration = clip.duration
            clip.close()
            return duration
        except Exception:
            try:
                import mutagen.mp3
                return mutagen.mp3.MP3(str(path)).info.length
            except Exception:
                # Last resort: average speaking rate (~150 wpm).
                return 8.0
