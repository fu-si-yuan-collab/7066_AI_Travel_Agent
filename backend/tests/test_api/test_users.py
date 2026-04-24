"""Tests for user registration and login."""

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    resp = await client.post("/api/v1/users/register", json={
        "email": "test@example.com",
        "password": "password123",
        "nickname": "Tester",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["nickname"] == "Tester"

    # Login
    resp = await client.post("/api/v1/users/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_duplicate_register(client):
    await client.post("/api/v1/users/register", json={
        "email": "dup@example.com",
        "password": "password123",
    })
    resp = await client.post("/api/v1/users/register", json={
        "email": "dup@example.com",
        "password": "password456",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/users/register", json={
        "email": "wrong@example.com",
        "password": "correct_password",
    })
    resp = await client.post("/api/v1/users/login", json={
        "email": "wrong@example.com",
        "password": "bad_password",
    })
    assert resp.status_code == 401
