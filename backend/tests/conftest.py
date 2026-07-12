import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://aoi:aoi@localhost:5432/aoi_studio_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key-not-real")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.main import app


@pytest.fixture(autouse=True)
async def _clean_db():
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE spec_drafts, structures, video_specs, projects, users, organizations "
                "RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client):
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "test-user@example.com",
            "password": "testpass123",
            "name": "Test User",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
async def project_id(auth_client):
    resp = await auth_client.post(
        "/api/v1/projects", json={"title": "Test Project", "video_type": "brand"}
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]

    resp = await auth_client.put(
        f"/api/v1/projects/{pid}/spec",
        json={
            "duration_sec": 30,
            "target_audience": "20-30代",
            "message": "message",
            "mood": "casual",
        },
    )
    assert resp.status_code == 200
    return pid
