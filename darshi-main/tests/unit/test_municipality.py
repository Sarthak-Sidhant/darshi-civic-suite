import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.routers.auth import get_current_user

# Mock dependencies
@pytest.fixture
def mock_db():
    with patch("app.routers.municipality.db_service") as mock:
        yield mock

@pytest.fixture
def mock_public_db():
    with patch("app.routers.public.db_service") as mock:
        yield mock

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_user():
    return {"username": "officer_sharma", "role": "citizen", "municipality_id": "ranchi"}

def test_get_dashboard_stats(test_client, mock_db, mock_user):
    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Setup mock
    mock_stats = {
        "total_reports": 100,
        "pending_reports": 10,
        "resolved_reports": 80,
        "avg_resolution_time_hours": 24.5,
        "active_alerts": 2,
        "reports_by_category": {"Road": 50, "Water": 30},
        "reports_by_status": {"pending": 10, "verified": 10, "resolved": 80}
    }
    mock_db.get_dashboard_stats = AsyncMock(return_value=mock_stats)

    # Execute
    response = test_client.get(
        "/api/v1/municipality/dashboard"
    )

    # Verify
    assert response.status_code == 200
    assert response.json() == mock_stats
    mock_db.get_dashboard_stats.assert_called_once()
    
    # Clean up
    app.dependency_overrides = {}

def test_broadcast_alert(test_client, mock_db, mock_user):
    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Setup mock
    mock_db.create_alert = AsyncMock(return_value="alert-uuid-123")
    
    alert_payload = {
        "title": "Heavy Rain",
        "description": "Flooding in Main Rd",
        "severity": "High",
        "category": "Safety",
        "radius_meters": 1000
    }

    # Execute
    response = test_client.post(
        "/api/v1/municipality/alert",
        json=alert_payload
    )

    # Verify
    assert response.status_code == 200
    assert response.json() == {"id": "alert-uuid-123", "status": "broadcasted"}
    mock_db.create_alert.assert_called_once()
    
    # Clean up
    app.dependency_overrides = {}

def test_get_public_alerts(test_client, mock_public_db):
    # Setup mock
    mock_alerts = [
        {"id": "1", "title": "Traffic Jam", "status": "ACTIVE"}
    ]
    mock_public_db.get_alerts = AsyncMock(return_value=mock_alerts)

    # Execute
    response = test_client.get("/api/v1/public/alerts?geohash=tu")

    # Verify
    assert response.status_code == 200
    assert response.json() == mock_alerts
    mock_public_db.get_alerts.assert_called_once_with(geohash="tu", status='ACTIVE', limit=20)
