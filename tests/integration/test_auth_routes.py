"""End-to-end exercise of the authentication flow.

Uses httpx.AsyncClient with FastAPI's ASGI transport so we never open
a real socket. The shared ``db_session`` fixture resets the schema so
each test starts with an empty users table.
"""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_register_login_whoami_flow(db_session):
    from backend.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Bootstrap the archive owner.
        r = await client.post(
            "/api/v1/auth/register",
            json={"username": "diogo", "password": "supersecret"},
        )
        assert r.status_code == 201, r.text
        token = r.json()["access_token"]
        assert token

        # Second registration must be refused — archive is single-owner.
        r_dup = await client.post(
            "/api/v1/auth/register",
            json={"username": "other", "password": "supersecret"},
        )
        assert r_dup.status_code == 409

        # Login with the same credentials (OAuth2 form-encoded).
        r = await client.post(
            "/api/v1/auth/login",
            data={"username": "diogo", "password": "supersecret"},
        )
        assert r.status_code == 200
        token = r.json()["access_token"]

        # Wrong password → 401.
        r = await client.post(
            "/api/v1/auth/login",
            data={"username": "diogo", "password": "wrong"},
        )
        assert r.status_code == 401

        # Authenticated whoami.
        r = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "diogo"
        assert body["is_owner"] is True

        # Unauthenticated whoami → 401.
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401
