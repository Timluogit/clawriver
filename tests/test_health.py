"""
Health endpoint tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_summary(client: AsyncClient):
    """Test the main health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    """Test liveness probe"""
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    """Test readiness probe"""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
