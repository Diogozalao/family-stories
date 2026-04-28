"""Authentication dependencies for FastAPI routes.

``get_current_user`` decodes the bearer token, looks up the user and
returns it. Routes that need authentication simply add it as a
dependency::

    @router.post("/something")
    async def handler(user: User = Depends(get_current_user)): ...
"""

import structlog
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import JWTError, decode_access_token
from backend.models.user import User

log = structlog.get_logger()

# ``auto_error=False`` so we can distinguish "missing token" from "bad token"
# — handy for returning clearer error messages.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


_CREDENTIALS_EXCEPTION = HTTPException(
    status_code = status.HTTP_401_UNAUTHORIZED,
    detail      = "Could not validate credentials",
    headers     = {"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db:    AsyncSession = Depends(get_db),
) -> User:
    """Resolve the JWT into the corresponding ``User`` row."""
    if not token:
        raise _CREDENTIALS_EXCEPTION

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise _CREDENTIALS_EXCEPTION
    except JWTError as exc:
        log.info("jwt_invalid", error=str(exc))
        raise _CREDENTIALS_EXCEPTION

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


async def get_current_user_query_or_header(
    header_token: str | None = Depends(oauth2_scheme),
    query_token:  str | None = Query(default=None, alias="token"),
    db:           AsyncSession = Depends(get_db),
) -> User:
    """Resolve a JWT from either the ``Authorization`` header or a
    ``?token=`` query string.

    Used for endpoints consumed by ``<img>``/``<video>`` tags which can't
    set custom headers.
    """
    token = header_token or query_token
    if not token:
        raise _CREDENTIALS_EXCEPTION

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise _CREDENTIALS_EXCEPTION
    except JWTError as exc:
        log.info("jwt_invalid", error=str(exc))
        raise _CREDENTIALS_EXCEPTION

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


async def get_current_owner(user: User = Depends(get_current_user)) -> User:
    """Stricter dependency: only the archive owner passes."""
    if not user.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner privileges required",
        )
    return user
