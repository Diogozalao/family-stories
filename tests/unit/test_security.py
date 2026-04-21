"""Unit tests for password hashing and JWT helpers."""

import pytest
from jose import JWTError

from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_verifiable_digest():
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith("$2")  # bcrypt identifier
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError):
        hash_password("")


def test_verify_password_handles_garbage_inputs():
    assert verify_password("", "") is False
    assert verify_password("pw", "not-a-bcrypt-hash") is False


def test_jwt_roundtrip_preserves_subject_and_extra():
    token = create_access_token(subject="42", extra={"username": "diogo"})
    decoded = decode_access_token(token)
    assert decoded["sub"] == "42"
    assert decoded["username"] == "diogo"
    assert "exp" in decoded and "iat" in decoded


def test_jwt_rejects_tampered_token():
    token = create_access_token(subject="1")
    tampered = token[:-4] + "AAAA"
    with pytest.raises(JWTError):
        decode_access_token(tampered)
