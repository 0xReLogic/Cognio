"""Integration tests for API endpoints."""

from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.database import db
from src.main import app


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Setup test database before each test."""
    settings.api_key = None
    db.db_path = ":memory:"
    db.connect()
    yield
    db.close()


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Test root endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Cognio"


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "db" in data
        assert "fts" in data
        assert "embedding_model" in data


@pytest.mark.asyncio
async def test_save_memory() -> None:
    """Test saving a memory."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/memory/save",
            json={"text": "Test memory", "project": "TEST", "tags": ["test", "example"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["saved"] is True
        assert data["duplicate"] is False
        assert data["reason"] == "created"
        assert "id" in data


@pytest.mark.asyncio
async def test_save_duplicate_memory() -> None:
    """Test saving a duplicate memory."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        memory_data = {"text": "Duplicate test", "project": "TEST", "tags": ["test"]}

        # Save first time
        response1 = await client.post("/memory/save", json=memory_data)
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["duplicate"] is False

        # Save second time (should be duplicate)
        response2 = await client.post("/memory/save", json=memory_data)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["duplicate"] is True
        assert data2["reason"] == "duplicate"
        assert data2["id"] == data1["id"]


@pytest.mark.asyncio
async def test_search_memory() -> None:
    """Test searching memories."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Save some test memories
        await client.post(
            "/memory/save",
            json={
                "text": "Python is a programming language",
                "project": "TEST",
                "tags": ["python"],
            },
        )
        await client.post(
            "/memory/save",
            json={
                "text": "JavaScript is used for web development",
                "project": "TEST",
                "tags": ["javascript"],
            },
        )

        # Search for Python
        response = await client.get(
            "/memory/search",
            params={"q": "programming language", "limit": 5, "threshold": 0.3},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
        assert data["results"][0]["score"] > 0.3


@pytest.mark.asyncio
async def test_list_memories() -> None:
    """Test listing memories."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Save multiple memories
        for i in range(5):
            await client.post(
                "/memory/save",
                json={"text": f"Memory {i}", "project": "TEST", "tags": [f"tag{i}"]},
            )

        # List all memories
        response = await client.get("/memory/list", params={"page": 1, "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert len(data["memories"]) == 5
        assert data["total_items"] == 5


@pytest.mark.asyncio
async def test_get_memory() -> None:
    """Test getting a single memory by ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Save a memory
        save_response = await client.post(
            "/memory/save",
            json={"text": "Test memory content", "project": "TEST", "tags": ["test"]},
        )
        memory_id = save_response.json()["id"]

        # Get the memory
        get_response = await client.get(f"/memory/{memory_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == memory_id
        assert data["text"] == "Test memory content"
        assert data["project"] == "TEST"
        assert "test" in data["tags"]

        # Try to get non-existent memory
        get_response2 = await client.get("/memory/nonexistent-id")
        assert get_response2.status_code == 404


@pytest.mark.asyncio
async def test_delete_memory() -> None:
    """Test deleting a memory."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Save a memory
        save_response = await client.post(
            "/memory/save", json={"text": "Memory to delete", "project": "TEST"}
        )
        memory_id = save_response.json()["id"]

        # Delete it
        delete_response = await client.delete(f"/memory/{memory_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

        # Try to delete again (should fail)
        delete_response2 = await client.delete(f"/memory/{memory_id}")
        assert delete_response2.status_code == 404


@pytest.mark.asyncio
async def test_get_stats() -> None:
    """Test getting statistics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Save some memories
        await client.post(
            "/memory/save", json={"text": "Memory 1", "project": "PROJECT_A", "tags": ["tag1"]}
        )
        await client.post(
            "/memory/save", json={"text": "Memory 2", "project": "PROJECT_B", "tags": ["tag2"]}
        )

        # Get stats
        response = await client.get("/memory/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_memories"] == 2
        assert data["total_projects"] == 2
        assert "memories_by_project" in data
        assert data["memories_by_project"]["PROJECT_A"] == 1
        assert data["memories_by_project"]["PROJECT_B"] == 1
