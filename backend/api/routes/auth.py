"""Auth-adjacent routes.

After the migration to Supabase Auth, signup / login / password-reset
/ delete-account are all handled by the Supabase client from the
frontend — they no longer hit FastAPI. The only thing left here is a
``/me`` introspection endpoint that lets the frontend confirm the
current bearer token is valid and obtain the user identity the backend
sees (useful for debugging and for hydrating UI state from the JWT).
"""

from fastapi import APIRouter, Depends

from backend.core.auth import User, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
async def whoami(user: User = Depends(get_current_user)):
    """Return the authenticated identity decoded from the Supabase JWT."""
    return {
        "id":    str(user.id),
        "email": user.email,
        "role":  user.role,
    }
