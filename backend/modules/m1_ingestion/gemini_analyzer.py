import google.generativeai as genai
import structlog
import json
import asyncio
from pathlib import Path
from PIL import Image
from backend.core.config import settings

log = structlog.get_logger()

ANALYSIS_PROMPT = """Analisa esta fotografia familiar e responde APENAS em JSON válido com esta estrutura exata:

{
  "description": "Descrição detalhada da fotografia em português (2-3 frases)",
  "people_count": número de pessoas visíveis (0 se nenhuma),
  "setting": "local/contexto (ex: 'sala de estar', 'jardim', 'praia', 'casamento')",
  "emotion": "emoção predominante (ex: 'alegria', 'nostalgia', 'celebração', 'quotidiano')",
  "tags": ["tag1", "tag2", "tag3"],
  "narrative_hint": "Uma frase sugerindo como esta foto poderia aparecer numa narrativa familiar",
  "estimated_decade": "década estimada (ex: '1980s', '1990s', 'desconhecido')"
}

Sê específico e sensível ao contexto familiar. Não inventes detalhes que não vês."""

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
            self.model = genai.GenerativeModel("gemini-2.5-flash")
            log.info("gemini_ready")
        except Exception as e:
            log.error("gemini_setup_error", error=str(e))

    def analyze(self, file_path: Path) -> dict:
        """Análise síncrona — usada pelo processador individual."""
        if not self.model:
            return self._fallback()
        try:
            img = Image.open(file_path)
            img.thumbnail((1024, 1024))
            response = self.model.generate_content([ANALYSIS_PROMPT, img])
            return self._parse(response.text)
        except Exception as e:
            log.error("gemini_analysis_error", file=str(file_path), error=str(e))
            return self._fallback()

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
