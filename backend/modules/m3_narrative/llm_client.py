import structlog
import ollama as ollama_client
from backend.core.config import settings

log = structlog.get_logger()

class LLMClient:
    def __init__(self):
        self._ollama_ok = self._check_ollama()
        if not self._ollama_ok:
            self._setup_gemini()
        log.info("llm_ready", backend=self.backend)

    def _check_ollama(self) -> bool:
        try:
            models = ollama_client.list()
            available = [m.model for m in models.models]
            found = any(settings.OLLAMA_MODEL in m for m in available)
            if found:
                log.info("ollama_found", model=settings.OLLAMA_MODEL)
            return found
        except Exception as e:
            log.warning("ollama_unavailable", error=str(e))
            return False

    def _setup_gemini(self):
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._gemini = genai.GenerativeModel("gemini-2.0-flash-001")

    def generate(self, prompt: str, max_tokens: int = 1500) -> str:
        if self._ollama_ok:
            return self._ollama_generate(prompt, max_tokens)
        return self._gemini_generate(prompt, max_tokens)

    def _ollama_generate(self, prompt: str, max_tokens: int) -> str:
        try:
            log.info("llm_generating", backend="ollama")
            response = ollama_client.generate(
                model   = settings.OLLAMA_MODEL,
                prompt  = prompt,
                options = {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                    "top_p":       0.9,
                    "repeat_penalty": 1.1,
                }
            )
            text = response.response.strip()
            log.info("llm_done", backend="ollama", chars=len(text))
            return text
        except Exception as e:
            log.error("ollama_error", error=str(e))
            if not self._ollama_ok:
                return "Erro ao gerar narrativa."
            self._setup_gemini()
            return self._gemini_generate(prompt, max_tokens)

    def _gemini_generate(self, prompt: str, max_tokens: int) -> str:
        try:
            import google.generativeai as genai
            log.info("llm_generating", backend="gemini_fallback")
            response = self._gemini.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                )
            )
            text = response.text.strip()
            log.info("llm_done", backend="gemini", chars=len(text))
            return text
        except Exception as e:
            log.error("gemini_error", error=str(e))
            return "Não foi possível gerar a narrativa. Tenta novamente mais tarde."

    @property
    def backend(self) -> str:
        return "ollama" if self._ollama_ok else "gemini-fallback"
