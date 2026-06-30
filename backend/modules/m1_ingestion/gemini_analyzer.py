import google.generativeai as genai
import structlog
import json
import asyncio
import re
import time
from pathlib import Path
from PIL import Image
from backend.core.config import settings

log = structlog.get_logger()

ANALYSIS_PROMPT = """Analisa esta fotografia familiar com atenção e responde APENAS em JSON válido com esta estrutura exata:

{
  "description": "Descrição rica em português (3-4 frases): quem ou o que se vê e o que estão a fazer; o ESPAÇO e o ambiente (interior ou exterior, a divisão da casa ou a paisagem, mobiliário e objetos presentes); a luz e a atmosfera; e a época que a roupa e os objetos sugerem.",
  "people_count": número de pessoas visíveis (0 se nenhuma),
  "setting": "o lugar e o espaço, de forma específica (ex: 'cozinha antiga com fogão a lenha', 'quintal com muro de pedra e roseiras', 'praia ao fim da tarde', 'salão de um casamento')",
  "emotion": "emoção predominante (ex: 'alegria', 'nostalgia', 'celebração', 'quotidiano')",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "narrative_hint": "Uma frase sugerindo como esta foto poderia surgir, de forma natural, numa narrativa familiar — incluindo uma transição para o espaço/momento.",
  "estimated_decade": "década estimada pelas roupas e objetos (ex: '1980s', '1990s', 'desconhecido')"
}

Observa com cuidado o ESPAÇO e os pormenores que situam a cena (o lugar, a época, os objetos, a atmosfera). Sê específico e sensível ao contexto familiar. NÃO inventes detalhes que não vês."""

class GeminiAnalyzer:
    def __init__(self):
        self.model = None
        self._setup()

    def _setup(self):
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("coloca"):
            log.warning("gemini_not_configured")
            return
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            log.info("gemini_ready")
        except Exception as e:
            log.error("gemini_setup_error", error=str(e))

    def analyze(self, file_path: Path) -> dict:
        """Análise síncrona — usada pelo processador individual.

        Free-tier Gemini is rate-limited (≈15 requests/min): uploading many
        photos at once hits **429 quota exceeded**. We retry a few times,
        honouring the ``retry_delay`` the API suggests (capped so an upload
        request never hangs too long). If it still fails, the caller marks
        the photo FAILED so it's visible and re-analysable later.
        """
        if not self.model:
            return self._fallback()
        try:
            img = Image.open(file_path)
            img.thumbnail((1024, 1024))
        except Exception as e:
            log.error("gemini_image_open_error", file=str(file_path), error=str(e))
            return self._fallback()

        for attempt in range(4):
            try:
                response = self.model.generate_content([ANALYSIS_PROMPT, img])
                return self._parse(response.text)
            except Exception as e:
                msg = str(e)
                is_429 = "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()
                if is_429 and attempt < 3:
                    wait = self._retry_after(msg, default=8 * (attempt + 1))
                    log.warning("gemini_429_retry", attempt=attempt + 1, wait=wait)
                    time.sleep(wait)
                    continue
                log.error("gemini_analysis_error", file=str(file_path), error=msg)
                return self._fallback()
        return self._fallback()

    @staticmethod
    def _retry_after(message: str, default: float) -> float:
        """Pull a ``retry_delay`` (seconds) out of a 429 message; cap it so a
        synchronous upload request never blocks for too long."""
        m = re.search(r"retry_delay\D+(\d+)", message) or re.search(r"in (\d+(?:\.\d+)?)s", message)
        secs = float(m.group(1)) if m else default
        return min(max(secs, 2.0), 30.0)

    async def analyze_batch(self, file_paths: list[Path]) -> list[dict]:
        """
        Analisa múltiplas fotos em paralelo.
        Limita a 5 chamadas simultâneas para não exceder rate limit do free tier.
        """
        semaphore = asyncio.Semaphore(5)

        async def analyze_one(path: Path) -> dict:
            async with semaphore:
                loop = asyncio.get_event_loop()
                # Corre a chamada síncrona ao Gemini numa thread separada
                return await loop.run_in_executor(None, self.analyze, path)

        tasks = [analyze_one(p) for p in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Substitui erros pelo fallback
        return [
            r if isinstance(r, dict) else self._fallback()
            for r in results
        ]

    def _parse(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            data = json.loads(text)
            return {
                "ai_description":    data.get("description"),
                "ai_people_count":   data.get("people_count", 0),
                "ai_setting":        data.get("setting"),
                "ai_emotion":        data.get("emotion"),
                "ai_tags":           data.get("tags", []),
                "ai_narrative_hint": data.get("narrative_hint"),
            }
        except json.JSONDecodeError:
            return self._fallback()

    def _fallback(self) -> dict:
        return {
            "ai_description":    None,
            "ai_people_count":   None,
            "ai_setting":        None,
            "ai_emotion":        None,
            "ai_tags":           [],
            "ai_narrative_hint": None,
        }
