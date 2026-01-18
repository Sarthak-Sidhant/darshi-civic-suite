"""
Test configuration and fixtures for Darshi backend tests.

Uses PostgreSQL + Redis stack (no Firebase/GCP dependencies).
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Set test environment BEFORE any imports
os.environ['ENVIRONMENT'] = 'test'
os.environ['GEMINI_API_KEY'] = 'test-key'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-min-32-chars'

# Database settings (PostgreSQL)
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_DB'] = 'darshi_test'
os.environ['POSTGRES_USER'] = 'test_user'
os.environ['POSTGRES_PASSWORD'] = 'test_password'
os.environ['DATABASE_URL'] = 'postgresql://test_user:test_password@localhost:5432/darshi_test'

# Redis settings
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'
os.environ['REDIS_PASSWORD'] = 'test_redis_password'
os.environ['REDIS_URL'] = 'redis://:test_redis_password@localhost:6379/0'

# R2/Storage settings (Cloudflare R2)
os.environ['R2_ENDPOINT'] = 'https://test.r2.cloudflarestorage.com'
os.environ['R2_ACCESS_KEY_ID'] = 'test_access_key'
os.environ['R2_SECRET_ACCESS_KEY'] = 'test_secret_key'
os.environ['R2_BUCKET_NAME'] = 'test-bucket'
os.environ['R2_PUBLIC_URL'] = 'https://test.r2.dev'

# OAuth settings
os.environ['GOOGLE_CLIENT_ID'] = 'test-google-client-id'
os.environ['GOOGLE_CLIENT_SECRET'] = 'test-google-client-secret'
os.environ['GITHUB_CLIENT_ID'] = 'test-github-client-id'
os.environ['GITHUB_CLIENT_SECRET'] = 'test-github-client-secret'

# Email settings
os.environ['RESEND_API_KEY'] = 'test-resend-api-key'

# Frontend URL
os.environ['FRONTEND_URL'] = 'http://localhost:5173'

# Mock external services that aren't installed in test env
sys.modules['resend'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

# Now safe to import app modules
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Test client for API requests"""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Sample user data for tests"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
        "lat": 24.5,
        "lng": 86.7,
        "location_address": "Test Location"
    }


@pytest.fixture
def mock_postgres():
    """Mock PostgreSQL database service"""
    with patch('app.services.postgres_service') as mock:
        mock.get_user_by_username = AsyncMock(return_value=None)
        mock.get_user_by_email = AsyncMock(return_value=None)
        mock.create_user = AsyncMock(return_value={"username": "testuser", "id": 1})
        mock.get_reports = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('app.core.redis_client.get_redis_client') as mock:
        redis_mock = MagicMock()
        redis_mock.ping.return_value = True
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        mock.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_storage():
    """Mock Cloudflare R2 storage"""
    with patch('app.services.storage_service') as mock:
        mock.upload_image = AsyncMock(return_value="https://test.r2.dev/test-image.webp")
        yield mock


@pytest.fixture
def auth_token():
    """Generate a valid JWT token for testing"""
    from app.services import auth_service
    return auth_service.create_access_token(
        data={"sub": "testuser"},
        user_type="citizen"
    )


@pytest.fixture
def admin_token():
    """Generate admin authentication token"""
    from app.services import auth_service
    return auth_service.create_admin_token({
        "username": "testadmin",
        "email": "admin@darshi.gov.in",
        "role": "super_admin"
    })
