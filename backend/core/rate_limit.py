"""Per-IP rate limiting using slowapi.

The limiter is a singleton shared across every route. Default limits are
applied automatically; endpoints can override the limit with the
``@limiter.limit(...)`` decorator.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.core.config import settings

limiter = Limiter(
    key_func       = get_remote_address,
    default_limits = [settings.RATE_LIMIT_DEFAULT],
    storage_uri    = "memory://",   # In-process store — fine for a single server.
    # headers_enabled is left at its default (False) because enabling it
    # requires every decorated route to accept a ``Response`` parameter,
    # which is intrusive and doesn't add value for a local-first app.
)
