"""Auth API integration tests."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_signup_returns_tokens(client):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "a@b.com", "password": "password123", "display_name": "A"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    await client.post("/api/v1/auth/signup", json={"email": "dup@b.com", "password": "password123"})
    resp = await client.post(
        "/api/v1/auth/signup", json={"email": "dup@b.com", "password": "password123"}
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "email_exists"


@pytest.mark.asyncio
async def test_login_and_me(client):
    await client.post("/api/v1/auth/signup", json={"email": "c@b.com", "password": "password123"})
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "c@b.com", "password": "password123"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "c@b.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/signup", json={"email": "d@b.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "d@b.com", "password": "nope"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_refresh_rotates_token(client):
    signup = await client.post(
        "/api/v1/auth/signup", json={"email": "e@b.com", "password": "password123"}
    )
    refresh = signup.json()["refresh_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    # The old refresh token is now revoked (rotation).
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reuse.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_token(client):
    resp = await client.get("/api/v1/patients")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh(client):
    signup = await client.post(
        "/api/v1/auth/signup", json={"email": "f@b.com", "password": "password123"}
    )
    refresh = signup.json()["refresh_token"]
    await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401
