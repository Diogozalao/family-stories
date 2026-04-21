"""Input validation for uploaded files.

We cannot trust the ``Content-Type`` header the client sends nor the
file extension — both are attacker-controlled. The validator inspects
the actual bytes (libmagic) and enforces a hard-coded allow-list of
media types and size limits.
"""

from dataclasses import dataclass
from pathlib import Path

import magic
import structlog
from fastapi import HTTPException, UploadFile, status

from backend.core.config import settings

log = structlog.get_logger()


# ── Allow lists ───────────────────────────────────────────────────────────
PHOTO_MIME_WHITELIST = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

GEDCOM_MIME_WHITELIST = {
    "text/plain",
    "application/x-gedcom",
    "text/vnd.familysearch.gedcom",  # modern libmagic recognises GEDCOM explicitly.
    "application/octet-stream",      # older libmagic falls back to this.
}

# First few bytes that identify well-known photo formats, used as a second
# layer next to libmagic so we catch edge cases where the installed magic
# database is out of date.
PHOTO_MAGIC_PREFIXES: tuple[bytes, ...] = (
    b"\xff\xd8\xff",                       # JPEG
    b"\x89PNG\r\n\x1a\n",                  # PNG
    b"RIFF",                               # WebP (RIFF container)
    b"\x00\x00\x00 ftypheic",              # HEIC (partial)
    b"\x00\x00\x00\x18ftypheic",
)


@dataclass
class ValidatedUpload:
    """The sanitized result of a successful upload validation."""

    content:   bytes
    mime_type: str
    size:      int
    suffix:    str


# ── Helpers ───────────────────────────────────────────────────────────────
def _reject(detail: str, *, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
    """Raise an HTTPException with structured logging."""
    log.warning("upload_rejected", detail=detail)
    raise HTTPException(status_code=status_code, detail=detail)


async def _read_capped(file: UploadFile, cap_bytes: int) -> bytes:
    """Read the upload without exceeding ``cap_bytes``.

    Reads are streamed in chunks so a malicious client cannot cause the
    server to allocate gigabytes before we decide to reject.
    """
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > cap_bytes:
            _reject(
                f"File exceeds the maximum size of {cap_bytes // (1024 * 1024)} MB",
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        chunks.append(chunk)
    return b"".join(chunks)


# ── Public API ────────────────────────────────────────────────────────────
async def validate_photo(file: UploadFile) -> ValidatedUpload:
    """Ensure ``file`` is a real, supported photo and return its bytes."""
    if not file.filename:
        _reject("Missing filename")

    cap = settings.MAX_PHOTO_SIZE_MB * 1024 * 1024
    content = await _read_capped(file, cap)

    if not content:
        _reject("Empty file")

    detected_mime = magic.from_buffer(content, mime=True) or "application/octet-stream"

    matches_magic_prefix = any(content.startswith(p) for p in PHOTO_MAGIC_PREFIXES)
    if detected_mime not in PHOTO_MIME_WHITELIST and not matches_magic_prefix:
        _reject(
            f"Unsupported photo type: {detected_mime}. "
            f"Accepted: {', '.join(sorted(PHOTO_MIME_WHITELIST))}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    return ValidatedUpload(
        content   = content,
        mime_type = detected_mime,
        size      = len(content),
        suffix    = Path(file.filename).suffix.lower(),
    )


async def validate_gedcom(file: UploadFile) -> ValidatedUpload:
    """Ensure ``file`` is a plausible GEDCOM document."""
    if not file.filename:
        _reject("Missing filename")

    cap = settings.MAX_GEDCOM_SIZE_MB * 1024 * 1024
    content = await _read_capped(file, cap)

    if not content:
        _reject("Empty file")

    # GEDCOM files must start with "0 HEAD" (possibly after a BOM).
    head = content.lstrip(b"\xef\xbb\xbf").lstrip()[:32]
    if not head.startswith(b"0 HEAD") and not head.startswith(b"0\tHEAD"):
        _reject("File does not look like a valid GEDCOM (missing '0 HEAD' record)")

    detected_mime = magic.from_buffer(content, mime=True) or "application/octet-stream"
    if detected_mime not in GEDCOM_MIME_WHITELIST:
        _reject(
            f"Unsupported GEDCOM container: {detected_mime}",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    return ValidatedUpload(
        content   = content,
        mime_type = detected_mime,
        size      = len(content),
        suffix    = ".ged",
    )
