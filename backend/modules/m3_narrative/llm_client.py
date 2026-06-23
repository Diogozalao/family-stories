import structlog
import ollama as ollama_client
from backend.core.config import settings

log = structlog.get_logger()

class LLMClient:
    """Cliente de geração de TEXTO (narrativas) com cascata de backends.

    Ordem de prioridade (texto):
        1. Ollama  — local, grátis (llama3.2:3b). Usado em dev.
        2. Groq    — nuvem, grátis (llama-3.3-70b). Backend de texto em produção.
        3. Gemini  — último recurso para texto.

    O **Gemini fica reservado para a VISÃO do M1** (análise de fotos): a sua
    quota grátis é limitada, por isso não queremos gastá-la a gerar texto. Só
    é usado para narrativas se o Ollama e o Groq falharem ambos.
    """

    def __init__(self):
        self._ollama_ok = self._check_ollama()
        self._groq_ok   = bool(settings.GROQ_API_KEY)
        self._gemini    = None                      # configurado de forma preguiçosa
        # Só preparamos o Gemini à cabeça se ele for mesmo o único backend de
        # texto disponível (sem Ollama e sem Groq).
        if not self._ollama_ok and not self._groq_ok:
            self._setup_gemini()
        log.info("llm_ready", backend=self.backend)

    @property
    def backend(self) -> str:
        if self._ollama_ok:
            return "ollama"
        if self._groq_ok:
            return "groq"
        return "gemini-fallback"

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
        # Texto: Ollama → Groq → Gemini (ver docstring da classe).
        if self._ollama_ok:
            return self._ollama_generate(prompt, max_tokens)
        if self._groq_ok:
            return self._groq_generate(prompt, max_tokens)
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
            # Fallback de texto: Groq primeiro, Gemini só em último caso.
            if self._groq_ok:
                return self._groq_generate(prompt, max_tokens, _prev_error=f"Ollama: {e}")
            self._setup_gemini()
            return self._gemini_generate(prompt, max_tokens, _ollama_error=str(e))

    def _groq_generate(self, prompt: str, max_tokens: int, _prev_error: str | None = None) -> str:
        """Gera texto via Groq (API compatível com OpenAI). Backend de texto
        preferido na nuvem — modelo aberto grande (llama-3.3-70b), free tier.

        Em caso de falha, recorre ao Gemini como último recurso (mesmo sendo
        reservado para a visão, é melhor do que falhar a geração).
        """
        from groq import Groq

        try:
            log.info("llm_generating", backend="groq", model=settings.GROQ_MODEL)
            client = Groq(api_key=settings.GROQ_API_KEY,
                          timeout=settings.GEMINI_TIMEOUT)
            resp = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            text = (resp.choices[0].message.content or "").strip()
            if not text:
                raise RuntimeError("resposta vazia do Groq")
            log.info("llm_done", backend="groq", chars=len(text))
            return text
        except Exception as groq_exc:                       # noqa: BLE001
            log.error("groq_error", error=str(groq_exc))
            self._setup_gemini()
            return self._gemini_generate(
                prompt, max_tokens,
                _ollama_error=_prev_error,
                _groq_error=str(groq_exc),
            )

    def _gemini_generate(self, prompt: str, max_tokens: int,
                         _ollama_error: str | None = None,
                         _groq_error: str | None = None) -> str:
        import google.generativeai as genai

        if self._gemini is None:
            self._setup_gemini()

        cfg = genai.GenerationConfig(max_output_tokens=max_tokens, temperature=0.7)
        # Bound each call so a hanging/slow API doesn't keep the task spinning
        # forever. One retry covers transient 5xx / network blips.
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

        # Todos os backends de texto falharam — propaga para a tarefa ser
        # marcada como ``failed`` em vez de guardar uma narrativa falsa.
        details = f"Gemini ({settings.GEMINI_TEXT_MODEL}): {last_exc}"
        if _groq_error:
            details = f"Groq ({settings.GROQ_MODEL}): {_groq_error}\n{details}"
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
    """Raised when the local LLM, Groq and the Gemini fallback all fail."""
