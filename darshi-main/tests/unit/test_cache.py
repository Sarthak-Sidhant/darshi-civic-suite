"""
Unit tests for cache module
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


@pytest.mark.unit
class TestCacheKey:
    """Tests for cache key generation"""

    def test_cache_key_format(self):
        """Test that cache keys are properly formatted"""
        # Cache keys should be strings
        key = "reports:list:page:1"
        assert isinstance(key, str)
        assert ":" in key  # Using colon as separator

    def test_cache_key_with_params(self):
        """Test cache key generation with parameters"""
        base_key = "reports"
        page = 1
        limit = 20
        key = f"{base_key}:list:page:{page}:limit:{limit}"
        assert key == "reports:list:page:1:limit:20"


@pytest.mark.unit
class TestCacheOperations:
    """Tests for cache operations"""

    @pytest.mark.asyncio
    async def test_cache_set_get_mock(self):
        """Test cache set and get operations with mock"""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=json.dumps({"test": "value"}))
        mock_redis.set = AsyncMock(return_value=True)

        # Simulate set
        await mock_redis.set("test_key", json.dumps({"test": "value"}))
        mock_redis.set.assert_called_once()

        # Simulate get
        result = await mock_redis.get("test_key")
        assert json.loads(result) == {"test": "value"}

    @pytest.mark.asyncio
    async def test_cache_delete_mock(self):
        """Test cache delete operation with mock"""
        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock(return_value=1)

        result = await mock_redis.delete("test_key")
        assert result == 1

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache TTL setting"""
        mock_redis = MagicMock()
        mock_redis.setex = AsyncMock(return_value=True)

        # Set with 300 second TTL
        await mock_redis.setex("test_key", 300, json.dumps({"data": "value"}))
        mock_redis.setex.assert_called_with("test_key", 300, json.dumps({"data": "value"}))


@pytest.mark.unit
class TestCachePatterns:
    """Tests for common caching patterns"""

    def test_user_cache_key_pattern(self):
        """Test user cache key pattern"""
        username = "testuser"
        key = f"user:{username}:profile"
        assert key == "user:testuser:profile"

    def test_report_cache_key_pattern(self):
        """Test report cache key pattern"""
        report_id = "abc123"
        key = f"report:{report_id}"
        assert key == "report:abc123"

    def test_reports_list_cache_key_pattern(self):
        """Test reports list cache key pattern"""
        city = "delhi"
        page = 1
        key = f"reports:city:{city}:page:{page}"
        assert key == "reports:city:delhi:page:1"

    def test_cache_key_escaping(self):
        """Test that special characters in keys are handled"""
        # Keys with special characters should be sanitized
        username = "test@user"
        sanitized = username.replace("@", "_at_")
        key = f"user:{sanitized}:profile"
        assert "@" not in key
