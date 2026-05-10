"""Authentication dependencies — Supabase edition.

This module used to ship a custom HS256 JWT flow with a local ``User``
table. After the migration to Supabase Auth, both the issuer and the
identity store moved out of this app: tokens are issued by Supabase Auth
and validated against its JWKS endpoint by
:mod:`backend.core.supabase_auth`.

We keep this module as the public import surface used by route handlers
(``from backend.core.auth import get_current_user``) so the route code
didn't all need to be changed at once. The ``User`` symbol is now an
alias for :class:`AuthenticatedUser`, which exposes a UUID ``id`` and an
``email``. Routes that previously relied on ``user.is_owner`` no longer
have that field — the multi-tenant model has no single "owner".
"""

from backend.core.supabase_auth import (
    AuthenticatedUser as User,
    get_current_user,
    get_current_user_query_or_header,
)

__all__ = ["User", "get_current_user", "get_current_user_query_or_header"]
