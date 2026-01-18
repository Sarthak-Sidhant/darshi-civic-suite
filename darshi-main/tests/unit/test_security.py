"""
Unit tests for security middleware
"""

import pytest
from unittest.mock import MagicMock
from app.core import security


@pytest.mark.unit
class TestInputSanitization:
    """Test input sanitization functions"""

    def test_sanitize_input_strip_tags(self):
        """Test sanitizing input with HTML tags stripped"""
        dirty = "<script>alert('xss')</script>Hello"
        clean = security.sanitize_input(dirty, strip_tags=True)

        assert "<script>" not in clean
        assert "</script>" not in clean
        # bleach strips tags but keeps text content
        assert "Hello" in clean

    def test_sanitize_input_allow_safe_tags(self):
        """Test sanitizing input allowing safe tags"""
        dirty = "<b>Bold</b> <script>alert('xss')</script> <p>Paragraph</p>"
        clean = security.sanitize_input(dirty, strip_tags=False)

        assert "<b>Bold</b>" in clean
        assert "<p>Paragraph</p>" in clean
        assert "<script>" not in clean
        # Script tags removed but content might remain - that's ok for text fields

    def test_sanitize_empty_input(self):
        """Test sanitizing empty/None input"""
        assert security.sanitize_input(None) is None
        assert security.sanitize_input("") == ""

    def test_sanitize_form_data(self):
        """Test sanitizing form data dictionary"""
        dirty_data = {
            "title": "<script>XSS</script>Title",
            "description": "<b>Bold</b> text <script>bad</script>",
            "user_id": "user@example.com",
            "count": 42  # Non-string value
        }

        clean_data = security.sanitize_form_data(dirty_data)

        # Title should strip all tags (tags removed, text preserved)
        assert "<script>" not in clean_data["title"]
        assert "</script>" not in clean_data["title"]
        assert "Title" in clean_data["title"]

        # Description should allow safe tags
        assert "<b>Bold</b>" in clean_data["description"]
        assert "<script>" not in clean_data["description"]
        assert "</script>" not in clean_data["description"]

        # Non-string values should pass through
        assert clean_data["count"] == 42


@pytest.mark.unit
class TestRateLimitHelpers:
    """Test rate limit helper functions"""

    def test_get_rate_limit_anonymous(self):
        """Test rate limit for anonymous users"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        limit = security.get_rate_limit(mock_request, "reports")
        assert "hour" in limit

    def test_get_user_tier_anonymous(self):
        """Test user tier detection for anonymous users"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        tier = security.get_user_tier(mock_request)
        assert tier == "anonymous"

    def test_get_user_tier_with_invalid_token(self):
        """Test user tier with invalid token"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer invalid_token"

        tier = security.get_user_tier(mock_request)
        assert tier == "anonymous"


@pytest.mark.unit
class TestCORSValidation:
    """Test CORS origin validation"""

    def test_validate_exact_match(self):
        """Test exact origin match"""
        allowed = ["http://localhost:5173", "http://localhost:8080"]
        assert security.validate_cors_origin("http://localhost:5173", allowed) is True
        assert security.validate_cors_origin("http://localhost:9000", allowed) is False

    def test_validate_wildcard_pattern(self):
        """Test wildcard pattern matching"""
        allowed = ["http://10.0.0.*"]
        assert security.validate_cors_origin("http://10.0.0.5", allowed) is True
        assert security.validate_cors_origin("http://10.0.0.100", allowed) is True
        assert security.validate_cors_origin("http://192.168.1.5", allowed) is False
