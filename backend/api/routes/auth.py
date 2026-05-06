"""Authentication routes: bootstrap owner, login, whoami.

The bootstrap endpoint (``POST /api/v1/auth/register``) only succeeds
the first time it is called — subsequent calls are refused because the
archive already has an owner. After that, only the owner can invite
additional users (not yet exposed).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.email import send_email
from backend.core.rate_limit import limiter
from backend.core.security import create_access_token, hash_password, verify_password
from backend.models.password_reset import PasswordResetToken
from backend.models.user import User


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password:     str = Field(min_length=8, max_length=256)


class DeleteAccountRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    confirm:          str = Field(description="Tem de ser exatamente 'APAGAR'")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:        str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=8, max_length=256)


def _hash_token(raw: str) -> str:
    """SHA-256 do token plaintext — apenas o digest fica em DB."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

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


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db:      AsyncSession = Depends(get_db),
):
    """Inicia o flow de reset de palavra-passe.

    Devolve sempre **202 Accepted** com a mesma resposta, exista ou não
    o utilizador — assim impede um atacante de descobrir contas
    válidas a partir do tempo de resposta ou do código de status.
    """
    result = await db.execute(select(User).where(User.username == payload.email))
    user   = result.scalar_one_or_none()

    # Resposta uniforme. Construímos sempre o mesmo payload no fim.
    masked_response = {
        "message": "Se a conta existir, foi enviado um link de reset para o email indicado.",
    }

    if not user or not user.is_active:
        log.info("forgot_password_unknown_email", email=payload.email)
        return masked_response

    # Token plaintext (entregue ao utilizador) + hash (guardado em BD).
    raw_token   = secrets.token_urlsafe(48)
    token_hash  = _hash_token(raw_token)
    expires_at  = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_TTL_MINUTES)

    db.add(PasswordResetToken(
        user_id    = user.id,
        token_hash = token_hash,
        expires_at = expires_at,
    ))
    await db.commit()

    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"

    body_text = (
        f"Olá,\n\n"
        f"Recebemos um pedido para repor a palavra-passe da tua conta no Living Memory.\n\n"
        f"Abre o link a seguir nas próximas {settings.PASSWORD_RESET_TOKEN_TTL_MINUTES} minutos:\n\n"
        f"{reset_url}\n\n"
        f"Se não foste tu a pedir, ignora este email — ninguém terá acesso à tua conta.\n\n"
        f"— Living Memory"
    )
    body_html = f"""\
<!doctype html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #292524;">
  <h1 style="font-family: Georgia, serif; font-size: 24px; margin-bottom: 8px;">Recuperar palavra-passe</h1>
  <p style="color: #57534e;">Recebemos um pedido para repor a palavra-passe da tua conta no Living Memory.</p>
  <p style="margin: 28px 0;">
    <a href="{reset_url}" style="display:inline-block;background:#C67B15;color:#fff;padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:600;">
      Definir nova palavra-passe
    </a>
  </p>
  <p style="font-size: 13px; color: #78716c;">O link expira em {settings.PASSWORD_RESET_TOKEN_TTL_MINUTES} minutos. Se não foste tu, ignora este email.</p>
  <p style="font-size: 12px; color: #a8a29e; margin-top: 32px;">— Living Memory</p>
</body></html>"""

    delivered = await send_email(
        to        = payload.email,
        subject   = "Living Memory — Repor palavra-passe",
        body_text = body_text,
        body_html = body_html,
    )

    log.info(
        "password_reset_link_issued",
        user_id   = user.id,
        delivered = delivered,
        # Em modo log-only, o link já está no record acima ("body=...");
        # aqui registamos só a metadata. Em modo SMTP-on, a entrega foi
        # confirmada pelo log do email.py.
    )
    return masked_response


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db:      AsyncSession = Depends(get_db),
):
    """Conclui o reset usando o token recebido por email.

    Validações:
      * token existe (lookup pelo hash sha256)
      * ainda dentro da janela de validade
      * nunca usado antes
    """
    token_hash = _hash_token(payload.token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    record = result.scalar_one_or_none()

    if record is None:
        log.info("password_reset_token_unknown")
        raise HTTPException(status_code=400, detail="Token inválido ou já utilizado.")

    now = datetime.now(UTC)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:           # SQLite retorna naive — assumimos UTC
        expires_at = expires_at.replace(tzinfo=UTC)

    if record.used_at is not None:
        log.info("password_reset_token_reused", token_id=record.id)
        raise HTTPException(status_code=400, detail="Token inválido ou já utilizado.")
    if expires_at < now:
        log.info("password_reset_token_expired", token_id=record.id)
        raise HTTPException(status_code=400, detail="O link expirou. Pede um novo.")

    user = await db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Token inválido.")

    user.hashed_password = hash_password(payload.new_password)
    record.used_at       = now
    await db.commit()

    log.info("password_reset_completed", user_id=user.id)


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def delete_account(
    request: Request,
    payload: DeleteAccountRequest,
    db:      AsyncSession = Depends(get_db),
    user:    User         = Depends(get_current_user),
):
    """Elimina a conta e **todos os dados** associados — fotos, histórias,
    vídeos, projetos, tarefas e ficheiros em disco.

    Requer:
      * a palavra-passe atual (defesa em profundidade contra token roubado)
      * a string literal ``APAGAR`` no campo ``confirm`` (evita cliques acidentais)

    Esta operação é **irreversível** e não tem fluxo de undo.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        log.info("delete_account_wrong_password", user_id=user.id)
        raise HTTPException(status_code=400, detail="Palavra-passe atual incorreta.")

    if payload.confirm.strip() != "APAGAR":
        raise HTTPException(
            status_code=400,
            detail="Confirma escrevendo APAGAR em maiúsculas.",
        )

    from pathlib import Path

    from backend.core.config import settings as _s
    from backend.models.media import MediaFile
    from backend.models.narrative import Story
    from backend.models.password_reset import PasswordResetToken
    from backend.models.project import Project, ProjectMedia
    from backend.models.task import TaskRecord
    from backend.models.timeline import Person, TimelineEvent
    from backend.models.video import VideoOutput

    log.info("delete_account_start", user_id=user.id, username=user.username)

    # 1. Apagar ficheiros em disco — fotos + vídeos.
    media_rows = (await db.execute(select(MediaFile))).scalars().all()
    for m in media_rows:
        if m.file_path:
            try:
                Path(m.file_path).unlink(missing_ok=True)
            except OSError as exc:
                log.warning("delete_account_file_unlink_failed", path=m.file_path, error=str(exc))

    video_rows = (await db.execute(select(VideoOutput))).scalars().all()
    for v in video_rows:
        if v.file_path:
            try:
                Path(v.file_path).unlink(missing_ok=True)
            except OSError as exc:
                log.warning("delete_account_file_unlink_failed", path=v.file_path, error=str(exc))

    # 2. Limpar pastas auxiliares (áudio TTS, GEDCOM, grafo) — best-effort.
    aux = [
        _s.PROCESSED_DIR / "audio",
        _s.PROCESSED_DIR / "videos",
        _s.PROCESSED_DIR / "family_graph.json",
        _s.RAW_DIR / "gedcom",
        _s.RAW_DIR / "photos",
    ]
    for path in aux:
        try:
            if path.is_dir():
                for child in path.iterdir():
                    if child.is_file():
                        child.unlink(missing_ok=True)
            elif path.is_file():
                path.unlink(missing_ok=True)
        except OSError as exc:
            log.warning("delete_account_aux_cleanup_failed", path=str(path), error=str(exc))

    # 3. Apagar registos da BD numa ordem segura quanto a FKs.
    from sqlalchemy import delete as sqla_delete
    for model in (
        VideoOutput, Story, ProjectMedia, Project,
        TimelineEvent, Person, MediaFile, TaskRecord, PasswordResetToken,
    ):
        await db.execute(sqla_delete(model))

    # 4. Por fim, o utilizador.
    await db.delete(user)
    await db.commit()

    log.info("delete_account_complete", user_id=user.id)


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
