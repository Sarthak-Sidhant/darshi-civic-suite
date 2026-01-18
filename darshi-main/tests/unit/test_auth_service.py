"""
Unit tests for auth_service
"""

import pytest
from datetime import timedelta
from app.services import auth_service


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functions"""

    def test_password_hash_and_verify(self):
        """Test password hashing and verification"""
        password = "abc123"  # Minimal password for bcrypt compatibility
        hashed = auth_service.get_password_hash(password)

        # Hash should not match plain password
        assert hashed != password

        # Verify should return True for correct password
        assert auth_service.verify_password(password, hashed) is True

        # Verify should return False for incorrect password
        assert auth_service.verify_password("WrongPassword", hashed) is False

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "xyz789"  # Minimal password for bcrypt compatibility
        hash1 = auth_service.get_password_hash(password)
        hash2 = auth_service.get_password_hash(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2

        # But both should verify correctly
        assert auth_service.verify_password(password, hash1) is True
        assert auth_service.verify_password(password, hash2) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "test@example.com", "email": "test@example.com", "role": "citizen"}
        token = auth_service.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token(self):
        """Test JWT token decoding"""
        data = {"sub": "test@example.com", "email": "test@example.com", "role": "citizen"}
        token = auth_service.create_access_token(data)

        payload = auth_service.decode_token(token)

        assert payload is not None
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "citizen"
        assert "exp" in payload  # Expiration should be present

    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        payload = auth_service.decode_token(invalid_token)

        assert payload is None

    def test_create_admin_token(self):
        """Test admin token creation with shorter expiration"""
        data = {"email": "admin@darshi.gov.in", "role": "super_admin"}
        admin_token = auth_service.create_admin_token(data)

        assert admin_token is not None
        payload = auth_service.decode_token(admin_token)
        assert payload["email"] == "admin@darshi.gov.in"

    def test_token_with_custom_expiration(self):
        """Test token creation with custom expiration"""
        data = {"sub": "test@example.com", "email": "test@example.com"}
        expires_delta = timedelta(minutes=5)
        token = auth_service.create_access_token(data, expires_delta=expires_delta)

        payload = auth_service.decode_token(token)
        assert payload is not None
        assert "exp" in payload
