"""Supabase Storage helpers — async, service-role authenticated.

We talk to the Storage REST API directly with ``httpx`` rather than via
``supabase-py`` because:

* The backend already depends on ``httpx`` everywhere else, so this
  avoids dragging in a second async surface.
* The Storage REST API is tiny (upload / sign / delete) — wrapping it
  by hand is shorter than configuring a second client.
* We always authenticate with the ``service_role`` key, which bypasses
  RLS at the database tier. The application-level ``user_id`` checks in
  the routes are what enforce isolation for backend-driven calls; the
  Storage RLS policies still apply to direct browser uploads.

All paths in Storage follow the convention ``{user_id}/{kind}/{name}``
so the bucket-level RLS policy ``(storage.foldername(name))[1] =
auth.uid()::text`` keeps direct browser access scoped per user.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import httpx
import structlog

from backend.core.config import settings

log = structlog.get_logger()


# Single bucket used for every media artefact (photos, videos, ...).
# The folder under the user_id distinguishes the kind.
BUCKET = "photos"


def object_key_for(user_id, kind: str, filename: str) -> str:
    """Compose the canonical Storage object key for a user's artefact."""
    return f"{user_id}/{kind}/{filename}"


def _api_base() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1"


def _auth_headers(content_type: Optional[str] = None) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey":        settings.SUPABASE_SERVICE_ROLE_KEY,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


async def upload_bytes(
    object_key:   str,
    content:      bytes,
    content_type: Optional[str] = None,
    upsert:       bool = True,
) -> None:
    """Upload ``content`` to ``BUCKET/{object_key}`` in Supabase Storage."""
    url = f"{_api_base()}/object/{BUCKET}/{object_key}"
    headers = _auth_headers(content_type or "application/octet-stream")
    if upsert:
        # The Storage API treats x-upsert=true as "overwrite if exists".
        headers["x-upsert"] = "true"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, content=content)
        if resp.status_code not in (200, 201):
            log.error("storage_upload_failed", key=object_key, status=resp.status_code, body=resp.text[:300])
            resp.raise_for_status()

    log.info("storage_upload_ok", key=object_key, bytes=len(content))


def upload_bytes_sync(
    object_key:   str,
    content:      bytes,
    content_type: Optional[str] = None,
) -> None:
    """Blocking variant — convenient for Celery workers that aren't async."""
    asyncio.run(upload_bytes(object_key, content, content_type))


async def download_to_disk(object_key: str, dest_path: Path) -> Path:
    """Download an object to a local path. Used by M4 to feed MoviePy."""
    url = f"{_api_base()}/object/{BUCKET}/{object_key}"
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=_auth_headers())
        if resp.status_code != 200:
            log.error("storage_download_failed", key=object_key, status=resp.status_code)
            resp.raise_for_status()
        dest_path.write_bytes(resp.content)

    return dest_path


async def delete_object(object_key: str) -> None:
    """Remove an object from the bucket. Idempotent — 404 is not an error."""
    url = f"{_api_base()}/object/{BUCKET}/{object_key}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(url, headers=_auth_headers())
        if resp.status_code not in (200, 204, 404):
            log.error("storage_delete_failed", key=object_key, status=resp.status_code)
            resp.raise_for_status()
    log.info("storage_delete_ok", key=object_key)


_signed_url_cache: dict[str, tuple[str, float]] = {}


async def cached_signed_url(object_key: str, expires_in: int = 3600, refresh_buffer: int = 300) -> str:
    """Memoised wrapper around ``create_signed_url``.

    Returns the same signed URL for ``object_key`` until ``refresh_buffer``
    seconds before it expires. Keeping the redirect target stable lets
    the browser cache the actual photo bytes across page navigations —
    otherwise every render of an ``<img>`` would trigger a fresh
    download even though nothing changed.
    """
    import time
    now = time.time()
    cached = _signed_url_cache.get(object_key)
    if cached and cached[1] - refresh_buffer > now:
        return cached[0]
    url = await create_signed_url(object_key, expires_in=expires_in)
    _signed_url_cache[object_key] = (url, now + expires_in)
    return url


def invalidate_signed_url(object_key: str) -> None:
    """Drop the cached signed URL for ``object_key`` (e.g. after delete)."""
    _signed_url_cache.pop(object_key, None)


async def create_signed_url(object_key: str, expires_in: int = 3600) -> str:
    """Return a time-limited URL the browser can hit without auth headers.

    The signed URL embeds a short-lived JWT signed by the Storage service
    that grants read access to a single object. Even though our bucket
    is private, this lets ``<img>``/``<video>`` tags load directly from
    Supabase without proxying bytes through FastAPI.
    """
    url = f"{_api_base()}/object/sign/{BUCKET}/{object_key}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            url,
            headers=_auth_headers("application/json"),
            json={"expiresIn": expires_in},
        )
        if resp.status_code != 200:
            log.error("storage_sign_failed", key=object_key, status=resp.status_code, body=resp.text[:300])
            resp.raise_for_status()
        signed = resp.json().get("signedURL") or resp.json().get("signedUrl")
        if not signed:
            raise RuntimeError("Supabase Storage did not return a signedURL")

    # Supabase normally returns a path-relative URL like
    # ``/object/sign/{bucket}/{path}?token=...``. We prepend the
    # ``/storage/v1`` API base so the browser hits the correct host.
    # When the response is already absolute we keep it as-is.
    if signed.startswith("/storage/v1/"):
        return f"{settings.SUPABASE_URL.rstrip('/')}{signed}"
    if signed.startswith("/"):
        return f"{_api_base()}{signed}"
    return signed
