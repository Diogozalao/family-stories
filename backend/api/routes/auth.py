"""Authentication routes: bootstrap owner, login, whoami.

The bootstrap endpoint (``POST /api/v1/auth/register``) only succeeds
the first time it is called — subsequent calls are refused because the
archive already has an owner. After that, only the owner can invite
additional users (not yet exposed).
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.rate_limit import limiter
from backend.core.security import create_access_token, hash_password, verify_password
from backend.models.user import User


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password:     str = Field(min_length=8, max_length=256)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
log    = structlog.get_logger()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8,  max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         dict


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register_owner(
    request: Request,
    payload: RegisterRequest,
    db:      AsyncSession = Depends(get_db),
):
    """Create the archive owner. Only works once per database."""
    existing = await db.execute(select(User).where(User.is_owner.is_(True)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner already exists. Use /auth/login instead.",
        )

    user = User(
        username        = payload.username,
        hashed_password = hash_password(payload.password),
        is_owner        = True,
        is_active       = True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    log.info("owner_created", username=user.username, user_id=user.id)

    token = create_access_token(subject=user.id, extra={"username": user.username})
    return TokenResponse(
        access_token = token,
        user         = {"id": user.id, "username": user.username, "is_owner": True},
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    form:    OAuth2PasswordRequestForm = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    """Exchange username + password for a JWT bearer token."""
    result = await db.execute(select(User).where(User.username == form.username))
    user   = result.scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_password):
        log.info("login_failed", username=form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")

    token = create_access_token(subject=user.id, extra={"username": user.username})
    log.info("login_ok", username=user.username, user_id=user.id)

    return TokenResponse(
        access_token = token,
        user         = {"id": user.id, "username": user.username, "is_owner": user.is_owner},
    )


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Change the authenticated user's password.

    Requires the *current* password as proof of identity, even though we
    already validated the bearer token — this is the standard pattern
    that prevents a stolen-but-still-valid token from silently locking
    the rightful owner out.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        log.info("password_change_wrong_current", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Palavra-passe atual incorreta",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova palavra-passe tem de ser diferente da atual",
        )

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    log.info("password_changed", user_id=user.id)


@router.get("/me")
async def whoami(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return {
        "id":         user.id,
        "username":   user.username,
        "is_owner":   user.is_owner,
        "is_active":  user.is_active,
        "created_at": str(user.created_at),
    }
