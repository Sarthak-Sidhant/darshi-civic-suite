"""Test health check endpoint"""
import pytest

def test_health_endpoint(client):
    """Test health check endpoint returns valid response"""
    response = client.get("/health")

    # In CI environment without database, health check returns 503
    # In production with database, it returns 200
    # Both are valid responses depending on environment
    assert response.status_code in [200, 503]

    data = response.json()
    assert "status" in data
    assert "service" in data

    # If healthy, check for database status
    if response.status_code == 200:
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
