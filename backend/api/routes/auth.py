"""Auth-adjacent routes.

After the migration to Supabase Auth, signup / login / password-reset
/ delete-account are all handled by the Supabase client from the
frontend — they no longer hit FastAPI. The only thing left here is a
``/me`` introspection endpoint that lets the frontend confirm the
current bearer token is valid and obtain the user identity the backend
sees (useful for debugging and for hydrating UI state from the JWT).
"""

import httpx
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import User, get_current_user
from backend.core.config import settings
from backend.core.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
log    = structlog.get_logger()


@router.get("/me")
async def whoami(user: User = Depends(get_current_user)):
    """Return the authenticated identity decoded from the Supabase JWT."""
    return {
        "id":    str(user.id),
        "email": user.email,
        "role":  user.role,
    }


async def _delete_supabase_auth_user(user_id) -> bool:
    """Delete the Supabase Auth user via the admin API (service role).

    This is the part the old front-end "delete account" never did — it only
    signed out, leaving the auth user alive, so the person could log straight
    back in. Best-effort: a failure is logged but doesn't undo the data wipe.
    """
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey":        settings.SUPABASE_SERVICE_ROLE_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(url, headers=headers)
        if resp.status_code in (200, 204):
            return True
        log.error("auth_user_delete_failed", status=resp.status_code, body=resp.text[:300])
        return False
    except Exception as exc:                                   # noqa: BLE001
        log.error("auth_user_delete_error", error=str(exc))
        return False


@router.delete("/account")
async def delete_account(
    db:   AsyncSession = Depends(get_db),
    user: User         = Depends(get_current_user),
):
    """Permanently delete the caller's account — data **and** the auth user.

    Replaces the old stub that only signed out (so the user could still log
    back in). Wipes every owned row, then removes the Supabase Auth user so
    the credentials stop working. Each table delete is defensive so one
    failure doesn't block the rest.
    """
    from backend.models.media import MediaFile
    from backend.models.narrative import Story
    from backend.models.project import Project
    from backend.models.task import TaskRecord
    from backend.models.timeline import Person, Relationship, TimelineEvent
    from backend.models.video import VideoOutput

    uid = user.id
    # Children before parents; FK cascades (relationships, project_media)
    # clean up the join tables.
    for model in (TaskRecord, VideoOutput, TimelineEvent, Story,
                  Relationship, Person, MediaFile, Project):
        try:
            await db.execute(sa_delete(model).where(model.user_id == uid))
        except Exception as exc:                               # noqa: BLE001
            log.warning("account_delete_table_failed", model=model.__name__, error=str(exc))
    await db.commit()

    auth_deleted = await _delete_supabase_auth_user(uid)
    log.info("account_deleted", user_id=str(uid), auth_deleted=auth_deleted)
    return {"deleted": True, "auth_user_deleted": auth_deleted}
