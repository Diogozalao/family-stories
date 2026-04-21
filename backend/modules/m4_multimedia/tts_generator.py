"""Text-to-speech narration generation.

Uses gTTS (Google Text-to-Speech). The ``pt`` voice is the closest match
for European Portuguese that gTTS offers; using ``tld='pt'`` pins the
endpoint to the Portuguese localisation and consistently picks the
European variant over the Brazilian one.
"""

from pathlib import Path

import structlog
from gtts import gTTS

log = structlog.get_logger()


class TTSGenerator:
    """Generate narration audio files from text."""

    def __init__(self, lang: str = "pt", tld: str = "pt"):
        self.lang = lang
        self.tld  = tld

    def generate(self, text: str, output_path: Path) -> float:
        """Synthesize ``text`` into an MP3 at ``output_path``.

        Returns the resulting audio duration in seconds.
        """
        try:
            tts = gTTS(text=text, lang=self.lang, tld=self.tld, slow=False)
            tts.save(str(output_path))
            log.info("tts_generated", path=str(output_path), chars=len(text))
            return self._get_duration(output_path)
        except Exception as exc:
            log.error("tts_error", error=str(exc))
            raise

    def generate_paragraphs(self, text: str, output_dir: Path) -> list[dict]:
        """Generate one MP3 per paragraph.

        Returns a list of ``{path, duration, text}`` for each paragraph
        successfully rendered.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        results: list[dict] = []
        for index, paragraph in enumerate(paragraphs):
            if not paragraph:
                continue
            out = output_dir / f"para_{index:02d}.mp3"
            try:
                tts = gTTS(text=paragraph, lang=self.lang, tld=self.tld, slow=False)
                tts.save(str(out))
                duration = self._get_duration(out)
                results.append({"path": out, "duration": duration, "text": paragraph})
                log.info("tts_paragraph", index=index, duration=round(duration, 1))
            except Exception as exc:
                log.warning("tts_paragraph_skip", index=index, error=str(exc))

        return results

    def _get_duration(self, path: Path) -> float:
        """Read the duration of an MP3 without loading the full file."""
        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(str(path))
            duration = clip.duration
            clip.close()
            return duration
        except Exception:
            # Fallback: parse MP3 header metadata directly.
            try:
                import mutagen.mp3
                return mutagen.mp3.MP3(str(path)).info.length
            except Exception:
                # Last resort: assume average speaking rate (~150 wpm).
                return 8.0
