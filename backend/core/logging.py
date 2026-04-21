"""Structured logging configuration.

Logs are emitted in two places simultaneously:
  * stdout (colourised, developer-friendly when DEBUG=True)
  * logs/app.log — rotating JSON file for post-mortem analysis

The same structlog logger is used everywhere in the codebase — no
module needs to call ``configure_logging`` itself; importing this
module as part of app startup is enough.
"""

import logging
import logging.handlers
import sys

import structlog

from backend.core.config import settings

_configured = False


def configure_logging() -> None:
    """Configure stdlib logging + structlog processors.

    Idempotent: safe to call multiple times (only the first call wires
    things up). Call once at application startup.
    """
    global _configured
    if _configured:
        return

    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Stdlib handlers: stdout + a rotating JSON file.
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    root.handlers.clear()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(stdout_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        filename    = settings.LOGS_DIR / "app.log",
        maxBytes    = 10 * 1024 * 1024,   # 10 MB per file.
        backupCount = 5,
        encoding    = "utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(file_handler)

    # Silence very chatty third-party libraries unless we are debugging.
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Structlog: console renderer when debugging (pretty colours), JSON
    # otherwise — the file handler always ends up with structured JSON
    # because both paths share the same processor chain.
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if settings.DEBUG and sys.stdout.isatty():
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors        = shared_processors + [renderer],
        wrapper_class     = structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO,
        ),
        logger_factory    = structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use = True,
    )

    _configured = True
    structlog.get_logger().info(
        "logging_configured",
        debug = settings.DEBUG,
        file  = str(settings.LOGS_DIR / "app.log"),
    )
