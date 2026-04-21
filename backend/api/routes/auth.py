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
