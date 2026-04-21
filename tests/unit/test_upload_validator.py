"""Unit tests for upload input validation."""

import io

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from backend.core.upload_validator import validate_gedcom, validate_photo


def _upload(filename: str, data: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(data))


def _jpeg_bytes(size: tuple[int, int] = (10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_validate_photo_accepts_jpeg():
    result = await validate_photo(_upload("pic.jpg", _jpeg_bytes()))
    assert result.mime_type.startswith("image/")
    assert result.size > 0
    assert result.suffix == ".jpg"


@pytest.mark.asyncio
async def test_validate_photo_rejects_text_disguised_as_jpg():
    with pytest.raises(HTTPException) as exc:
        await validate_photo(_upload("fake.jpg", b"this is clearly not an image"))
    assert exc.value.status_code in (400, 415)


@pytest.mark.asyncio
async def test_validate_photo_rejects_empty_file():
    with pytest.raises(HTTPException):
        await validate_photo(_upload("empty.jpg", b""))


@pytest.mark.asyncio
async def test_validate_photo_rejects_oversize(monkeypatch):
    from backend.core import upload_validator
    monkeypatch.setattr(upload_validator.settings, "MAX_PHOTO_SIZE_MB", 0)
    with pytest.raises(HTTPException) as exc:
        await validate_photo(_upload("big.jpg", _jpeg_bytes((50, 50))))
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_validate_gedcom_accepts_plausible_file():
    data = b"0 HEAD\n1 SOUR Custom\n0 @I1@ INDI\n1 NAME John /Doe/\n0 TRLR\n"
    result = await validate_gedcom(_upload("tree.ged", data))
    assert result.suffix == ".ged"
    assert b"HEAD" in result.content


@pytest.mark.asyncio
async def test_validate_gedcom_rejects_non_gedcom():
    with pytest.raises(HTTPException) as exc:
        await validate_gedcom(_upload("tree.ged", b"hello world\n"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_gedcom_strips_utf8_bom():
    data = b"\xef\xbb\xbf0 HEAD\n0 TRLR\n"
    result = await validate_gedcom(_upload("tree.ged", data))
    assert result.content.startswith(b"\xef\xbb\xbf0 HEAD")
