"""
Unit tests for custom exceptions
"""

import pytest
from app.core.exceptions import (
    DarshiBaseException,
    DatabaseError,
    StorageError,
    AIServiceError,
    GeocodingError,
    InvalidInputError,
    InvalidFileError,
    FileSizeExceededError,
    InvalidFileTypeError,
    InvalidCoordinatesError,
    AuthenticationError,
    InsufficientPermissionsError,
    DocumentNotFoundError,
    AIRateLimitError,
    DocumentAlreadyExistsError
)


@pytest.mark.unit
class TestBaseException:
    """Tests for base exception class"""

    def test_base_exception_message(self):
        """Test base exception with message"""
        exc = DarshiBaseException("Test error message")
        assert str(exc) == "Test error message"

    def test_base_exception_to_dict(self):
        """Test exception to_dict method"""
        exc = DarshiBaseException("Test error", details="Additional details")
        result = exc.to_dict()
        assert "error" in result
        assert result["error"]["message"] == "Test error"


@pytest.mark.unit
class TestDatabaseErrors:
    """Tests for database-related exceptions"""

    def test_database_error(self):
        """Test DatabaseError exception"""
        exc = DatabaseError("Connection failed", details="timeout")
        assert "Connection failed" in str(exc)
        assert isinstance(exc, DarshiBaseException)

    def test_database_error_with_context(self):
        """Test DatabaseError with context information"""
        exc = DatabaseError(
            message="Query failed",
            operation="select",
            collection="users"
        )
        # Extra kwargs are stored in extra dict
        assert exc.extra.get("operation") == "select"
        assert exc.extra.get("collection") == "users"


@pytest.mark.unit
class TestStorageErrors:
    """Tests for storage-related exceptions"""

    def test_storage_error(self):
        """Test StorageError exception"""
        exc = StorageError("Upload failed")
        assert "Upload failed" in str(exc)

    def test_storage_error_with_file_info(self):
        """Test StorageError with file information"""
        exc = StorageError(
            message="Upload failed",
            filename="test.jpg",
            bucket="test-bucket"
        )
        assert exc.extra.get("filename") == "test.jpg"
        assert exc.extra.get("bucket") == "test-bucket"


@pytest.mark.unit
class TestAIServiceErrors:
    """Tests for AI service exceptions"""

    def test_ai_service_error(self):
        """Test AIServiceError exception"""
        exc = AIServiceError("Gemini API error")
        assert "Gemini API error" in str(exc)

    def test_ai_service_error_with_retry_info(self):
        """Test AIServiceError with model information"""
        exc = AIServiceError(
            message="Rate limited",
            model="gemini-2.5-flash"
        )
        assert exc.extra.get("model") == "gemini-2.5-flash"


@pytest.mark.unit
class TestGeocodingErrors:
    """Tests for geocoding exceptions"""

    def test_geocoding_error(self):
        """Test GeocodingError exception"""
        exc = GeocodingError("Address not found")
        assert "Address not found" in str(exc)


@pytest.mark.unit
class TestValidationErrors:
    """Tests for validation exceptions"""

    def test_invalid_input_error(self):
        """Test InvalidInputError exception"""
        exc = InvalidInputError("Invalid email format")
        assert "Invalid email format" in str(exc)

    def test_invalid_file_error(self):
        """Test InvalidFileError exception"""
        exc = InvalidFileError("Corrupted file")
        assert isinstance(exc, DarshiBaseException)

    def test_file_size_exceeded_error(self):
        """Test FileSizeExceededError exception"""
        exc = FileSizeExceededError("File exceeds maximum size of 10MB")
        assert "10MB" in str(exc)

    def test_invalid_file_type_error(self):
        """Test InvalidFileTypeError exception"""
        exc = InvalidFileTypeError("Only image files allowed")
        assert "image" in str(exc)

    def test_invalid_coordinates_error(self):
        """Test InvalidCoordinatesError exception"""
        exc = InvalidCoordinatesError("Latitude must be between -90 and 90")
        assert "Latitude" in str(exc)


@pytest.mark.unit
class TestAuthErrors:
    """Tests for authentication/authorization exceptions"""

    def test_authentication_error(self):
        """Test AuthenticationError exception"""
        exc = AuthenticationError("Invalid token")
        assert "Invalid token" in str(exc)

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError exception"""
        exc = InsufficientPermissionsError("Admin access required")
        assert "Admin" in str(exc)


@pytest.mark.unit
class TestResourceErrors:
    """Tests for resource-related exceptions"""

    def test_not_found_error(self):
        """Test DocumentNotFoundError exception"""
        exc = DocumentNotFoundError("Report not found")
        assert "not found" in str(exc)

    def test_rate_limit_error(self):
        """Test AIRateLimitError exception"""
        exc = AIRateLimitError("Too many requests")
        assert "Too many" in str(exc)

    def test_duplicate_error(self):
        """Test DocumentAlreadyExistsError exception"""
        exc = DocumentAlreadyExistsError("Username already exists")
        assert "already exists" in str(exc)


@pytest.mark.unit
class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy"""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from base"""
        exceptions = [
            DatabaseError("test"),
            StorageError("test"),
            AIServiceError("test"),
            GeocodingError("test"),
            InvalidInputError("test"),
            InvalidFileError("test"),
            AuthenticationError("test"),
            DocumentNotFoundError("test")
        ]

        for exc in exceptions:
            assert isinstance(exc, DarshiBaseException)

    def test_exceptions_are_catchable_as_exception(self):
        """Test that custom exceptions can be caught as Exception"""
        try:
            raise DatabaseError("test error")
        except Exception as e:
            assert "test error" in str(e)
