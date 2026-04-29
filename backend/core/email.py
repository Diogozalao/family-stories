"""Email delivery — opcional, com fallback ``log-only``.

Quando ``settings.SMTP_ENABLED`` é ``False`` (default), nenhuma ligação
de rede é feita: o link gerado é apenas escrito no log estruturado.
Isto preserva a premissa local-first do projeto e ainda assim permite
demonstrar o flow inteiro durante a defesa (basta copiar o link do
terminal para o browser).

Quando ligado, usa-se ``smtplib`` da stdlib (sem dependências novas) e
o envio acontece num thread para não bloquear o loop async do FastAPI.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

import structlog

from backend.core.config import settings

log = structlog.get_logger()


def _build_message(to: str, subject: str, body_text: str, body_html: str | None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"]    = settings.SMTP_FROM
    msg["To"]      = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    return msg


def _send_sync(msg: EmailMessage) -> None:
    """Envio síncrono — chamado dentro de ``asyncio.to_thread``."""
    if settings.SMTP_USE_TLS:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)


async def send_email(
    *, to: str, subject: str, body_text: str, body_html: str | None = None,
) -> bool:
    """Envia (ou regista) um email. Devolve ``True`` se entregue.

    Em modo desligado, regista o assunto e o corpo no log do backend e
    devolve ``False``. O chamador pode usar este retorno para decidir
    a mensagem que mostra ao utilizador.
    """
    if not settings.SMTP_ENABLED:
        log.info(
            "email_disabled_falling_back_to_log",
            to       = to,
            subject  = subject,
            body     = body_text,
        )
        return False

    if not settings.SMTP_HOST:
        log.error("email_smtp_enabled_but_host_missing")
        return False

    msg = _build_message(to, subject, body_text, body_html)
    try:
        await asyncio.to_thread(_send_sync, msg)
        log.info("email_sent", to=to, subject=subject)
        return True
    except Exception as exc:                                    # noqa: BLE001
        log.error("email_send_failed", to=to, error=str(exc))
        return False
