"""Supabase JWT validation via JWKS.

Replaces the previous custom HS256 token flow. Tokens are now issued by
Supabase Auth (signed with the project's ECC P-256 key) and validated
here against the public JWKS endpoint exposed by Supabase.

The validator caches the JWKS document in memory for ``_JWKS_TTL`` seconds
to avoid hammering the endpoint on every request. The cache is keyed by
``kid`` so multiple signing keys (e.g. during a rotation window) all
resolve correctly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
import structlog
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import JWTError

from backend.core.config import settings

log = structlog.get_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="supabase-issued", auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code = status.HTTP_401_UNAUTHORIZED,
    detail      = "Could not validate credentials",
    headers     = {"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Lightweight identity extracted from the validated Supabase JWT.

    Replaces the previous ``User`` ORM model in dependency injection. The
    ``id`` is the Supabase ``auth.users.id`` UUID, which is what every
    domain table will reference via its ``user_id`` column.
    """
    id:    UUID
    email: str | None
    role:  str          # 'authenticated' for signed-in users; 'anon' otherwise.
    raw:   dict[str, Any]


_JWKS_TTL     = 600   # seconds — refresh JWKS at most every 10 minutes.
_jwks_cache:   dict[str, dict] = {}
_jwks_fetched: float = 0.0


async def _get_jwks() -> dict[str, dict]:
    """Return the active JWKS map (kid → JWK), refreshing if stale."""
    global _jwks_fetched, _jwks_cache

    now = time.time()
    if _jwks_cache and (now - _jwks_fetched) < _JWKS_TTL:
        return _jwks_cache

    url = settings.SUPABASE_JWKS_URL
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        doc = resp.json()

    _jwks_cache   = {k["kid"]: k for k in doc.get("keys", []) if k.get("kid")}
    _jwks_fetched = now
    log.info("supabase_jwks_refreshed", n_keys=len(_jwks_cache))
    return _jwks_cache


async def _decode_token(token: str) -> dict[str, Any]:
    """Verify signature + claims and return the JWT payload."""
    try:
        headers = jwt.get_unverified_header(token)
    except JWTError as exc:
        log.info("supabase_jwt_bad_header", error=str(exc))
        raise _CREDENTIALS_EXCEPTION

    kid = headers.get("kid")
    if not kid:
        log.info("supabase_jwt_missing_kid")
        raise _CREDENTIALS_EXCEPTION

    jwks = await _get_jwks()
    jwk  = jwks.get(kid)
    if not jwk:
        # Token may have been signed by a key just rotated in — force a refresh.
        global _jwks_fetched
        _jwks_fetched = 0.0
        jwks = await _get_jwks()
        jwk  = jwks.get(kid)
        if not jwk:
            log.info("supabase_jwt_unknown_kid", kid=kid)
            raise _CREDENTIALS_EXCEPTION

    try:
        payload = jwt.decode(
            token,
            jwk,
            algorithms = [jwk.get("alg", "ES256")],
            audience   = "authenticated",
            # Supabase tokens carry ``iss = <SUPABASE_URL>/auth/v1`` — we
            # don't pin it because it varies per environment and the kid
            # check + audience are already enough.
            options    = {"verify_iss": False},
        )
    except JWTError as exc:
        log.info("supabase_jwt_invalid", error=str(exc))
        raise _CREDENTIALS_EXCEPTION

    return payload


def _user_from_payload(payload: dict[str, Any]) -> AuthenticatedUser:
    sub = payload.get("sub")
    if not sub:
        raise _CREDENTIALS_EXCEPTION
    try:
        user_uuid = UUID(sub)
    except (ValueError, TypeError):
        raise _CREDENTIALS_EXCEPTION

    return AuthenticatedUser(
        id    = user_uuid,
        email = payload.get("email"),
        role  = payload.get("role", "authenticated"),
        raw   = payload,
    )


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency: validate the Supabase JWT and return the user."""
    if not token:
        raise _CREDENTIALS_EXCEPTION
    payload = await _decode_token(token)
    return _user_from_payload(payload)


async def get_current_user_query_or_header(
    header_token: str | None = Depends(oauth2_scheme),
    query_token:  str | None = Query(default=None, alias="token"),
) -> AuthenticatedUser:
    """Same as ``get_current_user`` but also accepts ``?token=`` — for
    endpoints used by ``<img>``/``<video>`` tags that can't set headers."""
    token = header_token or query_token
    if not token:
        raise _CREDENTIALS_EXCEPTION
    payload = await _decode_token(token)
    return _user_from_payload(payload)
