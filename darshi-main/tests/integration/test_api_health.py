"""
Integration tests for API health check endpoint
"""

import pytest


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test health check returns 200"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["service"] == "Darshi Backend"

    def test_health_check_includes_database_status(self, client):
        """Test health check includes database status"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "database" in data
