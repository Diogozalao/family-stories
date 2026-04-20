"""
Geração de narração por síntese de voz (Text-to-Speech).

Usa gTTS (Google Text-to-Speech) com suporte a português europeu.
A narrativa é dividida em parágrafos para melhor controlo do áudio.
"""

import structlog
from pathlib import Path
from gtts import gTTS

log = structlog.get_logger()


class TTSGenerator:
    def __init__(self, lang: str = "pt"):
        self.lang = lang

    def generate(self, text: str, output_path: Path) -> float:
        """
        Converte texto em áudio MP3.
        Retorna a duração em segundos.
        """
        try:
            tts = gTTS(text=text, lang=self.lang, slow=False)
            tts.save(str(output_path))
            log.info("tts_generated", path=str(output_path), chars=len(text))

            duration = self._get_duration(output_path)
            return duration

        except Exception as e:
            log.error("tts_error", error=str(e))
            raise

    def generate_paragraphs(self, text: str, output_dir: Path) -> list[dict]:
        """
        Divide a narrativa em parágrafos e gera um ficheiro de áudio por parágrafo.
        Retorna lista de {path, duration, text}.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]

        results = []
        for i, para in enumerate(paragraphs):
            if not para:
                continue
            out = output_dir / f"para_{i:02d}.mp3"
            try:
                tts = gTTS(text=para, lang=self.lang, slow=False)
                tts.save(str(out))
                dur = self._get_duration(out)
                results.append({"path": out, "duration": dur, "text": para})
                log.info("tts_paragraph", index=i, duration=round(dur, 1))
            except Exception as e:
                log.warning("tts_paragraph_skip", index=i, error=str(e))

        return results

    def _get_duration(self, path: Path) -> float:
        """Obtém duração de ficheiro MP3 sem carregar o ficheiro inteiro."""
        try:
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(str(path))
            dur = clip.duration
            clip.close()
            return dur
        except Exception:
            # Fallback: estima pela velocidade média de fala (150 palavras/min)
            try:
                import mutagen.mp3
                audio = mutagen.mp3.MP3(str(path))
                return audio.info.length
            except Exception:
                return 8.0
