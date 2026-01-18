"""
Unit tests for validation utilities
"""

import pytest
from app.core.validation import (
    validate_file_size,
    validate_file_type,
    validate_file,
    validate_latitude,
    validate_longitude,
    validate_coordinates,
    parse_location_string,
    validate_email,
    validate_username,
    validate_password,
    validate_text_length,
    validate_report_title,
    validate_report_description,
    validate_category,
    validate_severity,
    validate_status,
    validate_report_data,
    MAX_FILE_SIZE,
    ALLOWED_IMAGE_TYPES,
    VALID_CATEGORIES,
    VALID_STATUSES
)
from app.core.exceptions import (
    InvalidInputError,
    InvalidFileError,
    FileSizeExceededError,
    InvalidFileTypeError,
    InvalidCoordinatesError
)


@pytest.mark.unit
class TestFileValidation:
    """Tests for file validation functions"""

    def test_validate_file_size_valid(self):
        """Test valid file size"""
        # Should not raise
        validate_file_size(1024)  # 1KB
        validate_file_size(MAX_FILE_SIZE)  # Exactly max

    def test_validate_file_size_exceeds_max(self):
        """Test file size exceeding maximum"""
        with pytest.raises(FileSizeExceededError) as exc_info:
            validate_file_size(MAX_FILE_SIZE + 1)
        assert "exceeds maximum" in str(exc_info.value)

    def test_validate_file_type_valid(self):
        """Test valid file types"""
        for mime_type in ALLOWED_IMAGE_TYPES:
            validate_file_type(mime_type)

    def test_validate_file_type_invalid(self):
        """Test invalid file type"""
        with pytest.raises(InvalidFileTypeError):
            validate_file_type("application/pdf")

    def test_validate_file_type_missing(self):
        """Test missing content type"""
        with pytest.raises(InvalidFileTypeError) as exc_info:
            validate_file_type(None)
        assert "not specified" in str(exc_info.value)

    def test_validate_file_type_with_parameters(self):
        """Test content type with parameters (e.g., charset)"""
        validate_file_type("image/jpeg; charset=utf-8")

    def test_validate_file_type_with_filename(self):
        """Test file type validation with filename extension"""
        validate_file_type("image/jpeg", "test.jpg")
        validate_file_type("image/png", "photo.png")

    def test_validate_file_type_invalid_extension(self):
        """Test invalid file extension"""
        with pytest.raises(InvalidFileTypeError):
            validate_file_type("image/jpeg", "test.exe")

    def test_validate_file_empty(self):
        """Test empty file validation"""
        with pytest.raises(InvalidFileError) as exc_info:
            validate_file(b"", "image/jpeg")
        assert "Empty file" in str(exc_info.value)

    def test_validate_file_complete(self):
        """Test complete file validation"""
        # Should not raise
        validate_file(b"fake image content", "image/jpeg", "test.jpg")


@pytest.mark.unit
class TestCoordinateValidation:
    """Tests for coordinate validation functions"""

    def test_validate_latitude_valid(self):
        """Test valid latitudes"""
        validate_latitude(0)
        validate_latitude(45.5)
        validate_latitude(-45.5)
        validate_latitude(90)
        validate_latitude(-90)

    def test_validate_latitude_out_of_range(self):
        """Test latitude out of range"""
        with pytest.raises(InvalidCoordinatesError):
            validate_latitude(91)
        with pytest.raises(InvalidCoordinatesError):
            validate_latitude(-91)

    def test_validate_latitude_invalid_type(self):
        """Test latitude with invalid type"""
        with pytest.raises(InvalidCoordinatesError):
            validate_latitude("not a number")

    def test_validate_longitude_valid(self):
        """Test valid longitudes"""
        validate_longitude(0)
        validate_longitude(120.5)
        validate_longitude(-120.5)
        validate_longitude(180)
        validate_longitude(-180)

    def test_validate_longitude_out_of_range(self):
        """Test longitude out of range"""
        with pytest.raises(InvalidCoordinatesError):
            validate_longitude(181)
        with pytest.raises(InvalidCoordinatesError):
            validate_longitude(-181)

    def test_validate_coordinates_valid(self):
        """Test valid coordinate pairs"""
        validate_coordinates(23.5, 85.3)  # India
        validate_coordinates(-33.9, 151.2)  # Sydney

    def test_validate_coordinates_invalid(self):
        """Test invalid coordinate pairs"""
        with pytest.raises(InvalidCoordinatesError):
            validate_coordinates(100, 50)  # Invalid lat

    def test_parse_location_string_valid(self):
        """Test parsing valid location strings"""
        lat, lng = parse_location_string("23.5,85.3")
        assert lat == 23.5
        assert lng == 85.3

        lat, lng = parse_location_string(" 23.5 , 85.3 ")  # With spaces
        assert lat == 23.5
        assert lng == 85.3

    def test_parse_location_string_invalid_format(self):
        """Test parsing invalid location strings"""
        with pytest.raises(InvalidCoordinatesError):
            parse_location_string("invalid")
        with pytest.raises(InvalidCoordinatesError):
            parse_location_string("23.5")  # Missing longitude
        with pytest.raises(InvalidCoordinatesError):
            parse_location_string("23.5,85.3,100")  # Extra value


@pytest.mark.unit
class TestStringValidation:
    """Tests for string validation functions"""

    def test_validate_email_valid(self):
        """Test valid emails"""
        validate_email("test@example.com")
        validate_email("user.name@domain.co.in")
        validate_email("user+tag@example.org")

    def test_validate_email_invalid(self):
        """Test invalid emails"""
        with pytest.raises(InvalidInputError):
            validate_email("")
        with pytest.raises(InvalidInputError):
            validate_email("invalid-email")
        with pytest.raises(InvalidInputError):
            validate_email("@nodomain.com")
        with pytest.raises(InvalidInputError):
            validate_email("noemail@")

    def test_validate_email_too_long(self):
        """Test email that's too long (over 320 chars per RFC 5321)"""
        long_email = "a" * 310 + "@example.com"  # Over 320 chars total
        with pytest.raises(InvalidInputError) as exc_info:
            validate_email(long_email)
        assert "too long" in str(exc_info.value).lower() or "characters" in str(exc_info.value).lower()

    def test_validate_username_valid(self):
        """Test valid usernames"""
        validate_username("abc")  # Minimum length
        validate_username("user123")
        validate_username("test_user")
        validate_username("user-name")
        validate_username("a" * 30)  # Maximum length

    def test_validate_username_invalid(self):
        """Test invalid usernames"""
        with pytest.raises(InvalidInputError):
            validate_username("")  # Empty
        with pytest.raises(InvalidInputError):
            validate_username("ab")  # Too short
        with pytest.raises(InvalidInputError):
            validate_username("a" * 31)  # Too long
        with pytest.raises(InvalidInputError):
            validate_username("user@name")  # Invalid character

    def test_validate_password_valid(self):
        """Test valid passwords"""
        validate_password("Password1")
        validate_password("SecurePass123")

    def test_validate_password_invalid(self):
        """Test invalid passwords"""
        with pytest.raises(InvalidInputError):
            validate_password("")  # Empty
        with pytest.raises(InvalidInputError):
            validate_password("short")  # Too short
        with pytest.raises(InvalidInputError):
            validate_password("NoNumbers")  # No numbers

    def test_validate_password_too_long(self):
        """Test password that's too long"""
        with pytest.raises(InvalidInputError):
            validate_password("a" * 129 + "1")

    def test_validate_text_length(self):
        """Test text length validation"""
        validate_text_length("hello", "field", min_length=3, max_length=10)

        with pytest.raises(InvalidInputError):
            validate_text_length("hi", "field", min_length=3)

        with pytest.raises(InvalidInputError):
            validate_text_length("hello world", "field", max_length=5)


@pytest.mark.unit
class TestReportValidation:
    """Tests for report-related validation"""

    def test_validate_report_title_valid(self):
        """Test valid report titles"""
        validate_report_title("Pothole on Main Street")
        validate_report_title("Water leakage near building")

    def test_validate_report_title_invalid(self):
        """Test invalid report titles"""
        with pytest.raises(InvalidInputError):
            validate_report_title("")  # Empty
        with pytest.raises(InvalidInputError):
            validate_report_title("    ")  # Only whitespace
        with pytest.raises(InvalidInputError):
            validate_report_title("Pot")  # Too short
        with pytest.raises(InvalidInputError):
            validate_report_title("a" * 201)  # Too long

    def test_validate_report_description(self):
        """Test report description validation"""
        validate_report_description(None)  # Optional
        validate_report_description("")  # Empty OK
        validate_report_description("This is a valid description")

        with pytest.raises(InvalidInputError):
            validate_report_description("a" * 2001)  # Too long

    def test_validate_category_valid(self):
        """Test valid categories"""
        for category in VALID_CATEGORIES:
            validate_category(category)

    def test_validate_category_invalid(self):
        """Test invalid category"""
        with pytest.raises(InvalidInputError):
            validate_category("InvalidCategory")

    def test_validate_severity_valid(self):
        """Test valid severity levels"""
        for i in range(11):  # 0-10
            validate_severity(i)

    def test_validate_severity_invalid(self):
        """Test invalid severity levels"""
        with pytest.raises(InvalidInputError):
            validate_severity(-1)
        with pytest.raises(InvalidInputError):
            validate_severity(11)
        with pytest.raises(InvalidInputError):
            validate_severity(5.5)  # Not an integer

    def test_validate_status_valid(self):
        """Test valid statuses"""
        for status in VALID_STATUSES:
            validate_status(status)

    def test_validate_status_invalid(self):
        """Test invalid status"""
        with pytest.raises(InvalidInputError):
            validate_status("INVALID_STATUS")

    def test_validate_report_data_complete(self):
        """Test complete report data validation"""
        lat, lng = validate_report_data(
            title="Pothole on Main Street",
            location="23.5,85.3",
            description="Large pothole causing traffic issues",
            username="testuser"
        )
        assert lat == 23.5
        assert lng == 85.3

    def test_validate_report_data_minimal(self):
        """Test minimal report data validation"""
        lat, lng = validate_report_data(
            title="Pothole on Main Street",
            location="23.5,85.3"
        )
        assert lat == 23.5
        assert lng == 85.3
