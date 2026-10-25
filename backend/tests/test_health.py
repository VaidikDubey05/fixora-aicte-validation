from unittest.mock import patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Fixora"
    assert "/api/health" in data["health"]


@pytest.mark.asyncio
async def test_health_healthy(client: AsyncClient):
    with patch(
        "app.routers.health.check_postgres",
        return_value={"status": "connected", "latency_ms": 1.25, "details": "operational"},
    ), patch(
        "app.routers.health.check_mongo",
        return_value={"status": "connected", "latency_ms": 0.82, "details": "operational"},
    ):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["postgres"]["status"] == "connected"
        assert data["postgres"]["latency_ms"] == 1.25
        assert data["mongodb"]["status"] == "connected"
        assert data["mongodb"]["latency_ms"] == 0.82
        assert "timestamp" in data
        assert "environment" in data


@pytest.mark.asyncio
async def test_health_degraded_postgres(client: AsyncClient):
    with patch(
        "app.routers.health.check_postgres",
        return_value={"status": "unavailable", "latency_ms": None, "details": "Connection refused"},
    ), patch(
        "app.routers.health.check_mongo",
        return_value={"status": "connected", "latency_ms": 0.95, "details": "operational"},
    ):
        response = await client.get("/api/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["postgres"]["status"] == "unavailable"
        assert data["mongodb"]["status"] == "connected"


@pytest.mark.asyncio
async def test_health_degraded_mongo(client: AsyncClient):
    with patch(
        "app.routers.health.check_postgres",
        return_value={"status": "connected", "latency_ms": 1.5, "details": "operational"},
    ), patch(
        "app.routers.health.check_mongo",
        return_value={"status": "unavailable", "latency_ms": None, "details": "Timeout"},
    ):
        response = await client.get("/api/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["postgres"]["status"] == "connected"
        assert data["mongodb"]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_error_envelope_format(client: AsyncClient):
    # Request a non-existent path to trigger 404
    response = await client.get("/api/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
