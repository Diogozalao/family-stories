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

    @property
    def backend(self) -> str:
        return "ollama" if self._ollama_ok else "gemini-fallback"

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
        self._gemini = genai.GenerativeModel(settings.GEMINI_TEXT_MODEL)

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
            self._setup_gemini()
            return self._gemini_generate(prompt, max_tokens, _ollama_error=str(e))

    def _gemini_generate(self, prompt: str, max_tokens: int, _ollama_error: str | None = None) -> str:
        import google.generativeai as genai

        cfg = genai.GenerationConfig(max_output_tokens=max_tokens, temperature=0.7)
        # Bound each call so a hanging/slow API doesn't keep the task spinning
        # forever (it used to have no timeout, which is why a failing model
        # looked like "takes ages, then errors"). One retry covers transient
        # 5xx / network blips.
        last_exc: Exception | None = None
        for attempt in (1, 2):
            try:
                log.info("llm_generating", backend="gemini_fallback",
                         model=settings.GEMINI_TEXT_MODEL, attempt=attempt)
                response = self._gemini.generate_content(
                    prompt,
                    generation_config=cfg,
                    request_options={"timeout": settings.GEMINI_TIMEOUT},
                )
                text = (getattr(response, "text", None) or "").strip()
                if not text:
                    # Empty text usually means the response was blocked or hit
                    # a finish reason other than STOP — surface that clearly.
                    reason = self._blocked_reason(response)
                    raise RuntimeError(f"resposta vazia do Gemini ({reason})")
                log.info("llm_done", backend="gemini", chars=len(text))
                return text
            except Exception as e:                              # noqa: BLE001
                last_exc = e
                log.warning("gemini_attempt_failed", attempt=attempt, error=str(e))

        log.error("gemini_error", error=str(last_exc))
        # Both backends failed — propagate so the caller can mark the
        # task/story as ``failed`` instead of saving a fake narrative.
        details = f"Gemini ({settings.GEMINI_TEXT_MODEL}): {last_exc}"
        if _ollama_error:
            details = f"Ollama: {_ollama_error}\n{details}"
        raise LLMUnavailableError(details) from last_exc

    @staticmethod
    def _blocked_reason(response) -> str:
        """Extract a human hint for why a Gemini response carried no text."""
        try:
            fb = getattr(response, "prompt_feedback", None)
            if fb and getattr(fb, "block_reason", None):
                return f"bloqueado: {fb.block_reason}"
            cands = getattr(response, "candidates", None) or []
            if cands:
                return f"finish_reason={getattr(cands[0], 'finish_reason', '?')}"
        except Exception:                                       # noqa: BLE001
            pass
        return "sem detalhe"


class LLMUnavailableError(RuntimeError):
    """Raised when both the local LLM and the Gemini fallback fail."""
