"""
Input validation utilities for Darshi application.

Provides comprehensive validation for user inputs, files, coordinates,
and other data to ensure robustness and security.
"""

import re
from typing import Optional, Tuple
from app.core.exceptions import (
    InvalidInputError,
    InvalidFileError,
    FileSizeExceededError,
    InvalidFileTypeError,
    InvalidCoordinatesError
)


# ============================================================================
# FILE VALIDATION
# ============================================================================

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed image MIME types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif"
}

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".heic",
    ".heif"
}


def validate_file_size(file_size: int, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Validate file size.

    Args:
        file_size: Size in bytes
        max_size: Maximum allowed size in bytes

    Raises:
        FileSizeExceededError: If file exceeds maximum size
    """
    if file_size > max_size:
        raise FileSizeExceededError(
            message=f"File size {file_size} bytes exceeds maximum {max_size} bytes",
            details=f"Maximum allowed: {max_size / (1024*1024):.1f}MB, got: {file_size / (1024*1024):.1f}MB"
        )


def validate_file_type(
    content_type: Optional[str],
    filename: Optional[str] = None,
    allowed_types: set = ALLOWED_IMAGE_TYPES
) -> None:
    """
    Validate file type.

    Args:
        content_type: MIME type
        filename: Optional filename for extension check
        allowed_types: Set of allowed MIME types

    Raises:
        InvalidFileTypeError: If file type is not allowed
    """
    if not content_type:
        raise InvalidFileTypeError(
            message="File type not specified",
            details="Content-Type header missing"
        )

    # Normalize content type (remove parameters)
    normalized_type = content_type.split(';')[0].strip().lower()

    if normalized_type not in allowed_types:
        raise InvalidFileTypeError(
            message=f"File type '{normalized_type}' not allowed",
            details=f"Allowed types: {', '.join(allowed_types)}"
        )

    # Additional check: validate extension if filename provided
    if filename:
        extension = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if extension and extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise InvalidFileTypeError(
                message=f"File extension '{extension}' not allowed",
                details=f"Allowed extensions: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )


def validate_file(
    file_bytes: bytes,
    content_type: Optional[str],
    filename: Optional[str] = None,
    max_size: int = MAX_FILE_SIZE
) -> None:
    """
    Comprehensive file validation.

    Args:
        file_bytes: File content
        content_type: MIME type
        filename: Optional filename
        max_size: Maximum file size

    Raises:
        InvalidFileError: If file is invalid
        FileSizeExceededError: If file is too large
        InvalidFileTypeError: If file type is not allowed
    """
    if not file_bytes:
        raise InvalidFileError(
            message="Empty file",
            details="File has no content"
        )

    validate_file_size(len(file_bytes), max_size)
    validate_file_type(content_type, filename)


# ============================================================================
# COORDINATE VALIDATION
# ============================================================================

def validate_latitude(lat: float) -> None:
    """
    Validate latitude value.

    Args:
        lat: Latitude value

    Raises:
        InvalidCoordinatesError: If latitude is invalid
    """
    if not isinstance(lat, (int, float)):
        raise InvalidCoordinatesError(
            message="Latitude must be a number",
            latitude=lat
        )

    if not -90 <= lat <= 90:
        raise InvalidCoordinatesError(
            message=f"Latitude {lat} out of range [-90, 90]",
            latitude=lat
        )


def validate_longitude(lng: float) -> None:
    """
    Validate longitude value.

    Args:
        lng: Longitude value

    Raises:
        InvalidCoordinatesError: If longitude is invalid
    """
    if not isinstance(lng, (int, float)):
        raise InvalidCoordinatesError(
            message="Longitude must be a number",
            longitude=lng
        )

    if not -180 <= lng <= 180:
        raise InvalidCoordinatesError(
            message=f"Longitude {lng} out of range [-180, 180]",
            longitude=lng
        )


def validate_coordinates(lat: float, lng: float) -> None:
    """
    Validate latitude and longitude.

    Args:
        lat: Latitude value
        lng: Longitude value

    Raises:
        InvalidCoordinatesError: If coordinates are invalid
    """
    validate_latitude(lat)
    validate_longitude(lng)


def parse_location_string(location: str) -> Tuple[float, float]:
    """
    Parse location string into lat/lng.

    Args:
        location: Location string in format "lat,lng"

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        InvalidCoordinatesError: If location string is invalid
    """
    try:
        parts = location.split(',')
        if len(parts) != 2:
            raise ValueError("Must contain exactly one comma")

        lat_str, lng_str = parts
        lat = float(lat_str.strip())
        lng = float(lng_str.strip())

        validate_coordinates(lat, lng)

        return lat, lng
    except ValueError as e:
        raise InvalidCoordinatesError(
            message=f"Invalid location format: {location}",
            details=f"Expected 'lat,lng' format. Error: {str(e)}"
        )


# ============================================================================
# STRING VALIDATION
# ============================================================================

def validate_email(email: str) -> None:
    """
    Validate email format.

    Args:
        email: Email address

    Raises:
        InvalidInputError: If email is invalid
    """
    if not email:
        raise InvalidInputError(
            message="Email is required",
            field="email"
        )

    # Basic email regex (RFC 5322 simplified)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        raise InvalidInputError(
            message=f"Invalid email format: {email}",
            field="email"
        )

    if len(email) > 320:  # RFC 5321
        raise InvalidInputError(
            message="Email too long (max 320 characters)",
            field="email"
        )


def validate_username(username: str) -> None:
    """
    Validate username format.

    Args:
        username: Username

    Raises:
        InvalidInputError: If username is invalid
    """
    if not username:
        raise InvalidInputError(
            message="Username is required",
            field="username"
        )

    if len(username) < 3:
        raise InvalidInputError(
            message="Username must be at least 3 characters",
            field="username"
        )

    if len(username) > 30:
        raise InvalidInputError(
            message="Username must be at most 30 characters",
            field="username"
        )

    # Allow alphanumeric, underscore, hyphen
    username_pattern = r'^[a-zA-Z0-9_-]+$'

    if not re.match(username_pattern, username):
        raise InvalidInputError(
            message="Username can only contain letters, numbers, underscores, and hyphens",
            field="username"
        )


def validate_password(password: str, min_length: int = 8) -> None:
    """
    Validate password strength.

    Args:
        password: Password
        min_length: Minimum password length

    Raises:
        InvalidInputError: If password is invalid
    """
    if not password:
        raise InvalidInputError(
            message="Password is required",
            field="password"
        )

    if len(password) < min_length:
        raise InvalidInputError(
            message=f"Password must be at least {min_length} characters",
            field="password"
        )

    if len(password) > 128:
        raise InvalidInputError(
            message="Password must be at most 128 characters",
            field="password"
        )

    # Check for at least one number
    if not re.search(r'\d', password):
        raise InvalidInputError(
            message="Password must contain at least one number",
            field="password"
        )

    # Check for at least one letter
    if not re.search(r'[a-zA-Z]', password):
        raise InvalidInputError(
            message="Password must contain at least one letter",
            field="password"
        )


def validate_text_length(
    text: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> None:
    """
    Validate text length.

    Args:
        text: Text to validate
        field_name: Name of field for error messages
        min_length: Minimum length
        max_length: Maximum length

    Raises:
        InvalidInputError: If text length is invalid
    """
    if min_length is not None and len(text) < min_length:
        raise InvalidInputError(
            message=f"{field_name} must be at least {min_length} characters",
            field=field_name
        )

    if max_length is not None and len(text) > max_length:
        raise InvalidInputError(
            message=f"{field_name} must be at most {max_length} characters",
            field=field_name
        )


def validate_report_title(title: str) -> None:
    """
    Validate report title.

    Args:
        title: Report title

    Raises:
        InvalidInputError: If title is invalid
    """
    if not title or not title.strip():
        raise InvalidInputError(
            message="Report title is required",
            field="title"
        )

    validate_text_length(title, "Title", min_length=5, max_length=200)


def validate_report_description(description: Optional[str]) -> None:
    """
    Validate report description.

    Args:
        description: Report description

    Raises:
        InvalidInputError: If description is invalid
    """
    if description is not None and description.strip():
        validate_text_length(description, "Description", max_length=2000)


# ============================================================================
# CATEGORY VALIDATION
# ============================================================================

VALID_CATEGORIES = {
    "Pothole",
    "Garbage",
    "Streetlight",
    "Water Supply",
    "Drainage",
    "Road Damage",
    "Traffic Signal",
    "Public Property",
    "Other",
    "Uncategorized"
}


def validate_category(category: str) -> None:
    """
    Validate report category.

    Args:
        category: Category name

    Raises:
        InvalidInputError: If category is invalid
    """
    if category not in VALID_CATEGORIES:
        raise InvalidInputError(
            message=f"Invalid category: {category}",
            field="category",
            details=f"Allowed categories: {', '.join(VALID_CATEGORIES)}"
        )


# ============================================================================
# SEVERITY VALIDATION
# ============================================================================

def validate_severity(severity: int) -> None:
    """
    Validate severity level.

    Args:
        severity: Severity level (0-10)

    Raises:
        InvalidInputError: If severity is invalid
    """
    if not isinstance(severity, int):
        raise InvalidInputError(
            message="Severity must be an integer",
            field="severity"
        )

    if not 0 <= severity <= 10:
        raise InvalidInputError(
            message=f"Severity must be between 0 and 10, got {severity}",
            field="severity"
        )


# ============================================================================
# STATUS VALIDATION
# ============================================================================

VALID_STATUSES = {
    "PENDING_VERIFICATION",
    "VERIFIED",
    "REJECTED",
    "DUPLICATE",
    "IN_PROGRESS",
    "RESOLVED",
    "FLAGGED"
}


def validate_status(status: str) -> None:
    """
    Validate report status.

    Args:
        status: Status value

    Raises:
        InvalidInputError: If status is invalid
    """
    if status not in VALID_STATUSES:
        raise InvalidInputError(
            message=f"Invalid status: {status}",
            field="status",
            details=f"Allowed statuses: {', '.join(VALID_STATUSES)}"
        )


# ============================================================================
# LOCATION VALIDATION (City/State/Country)
# ============================================================================

def validate_city(city: str) -> None:
    """
    Validate city name.

    Args:
        city: City name

    Raises:
        InvalidInputError: If city is invalid
    """
    if not city:
        raise InvalidInputError(
            message="City is required",
            field="city"
        )

    city_clean = city.strip()

    if not city_clean:
        raise InvalidInputError(
            message="City cannot be empty or whitespace only",
            field="city"
        )

    validate_text_length(city_clean, "City", min_length=2, max_length=100)


def validate_state(state: str, valid_states: Optional[set] = None) -> None:
    """
    Validate state name.

    Args:
        state: State name
        valid_states: Optional set of valid state names to check against

    Raises:
        InvalidInputError: If state is invalid
    """
    if not state:
        raise InvalidInputError(
            message="State is required",
            field="state"
        )

    state_clean = state.strip()

    if not state_clean:
        raise InvalidInputError(
            message="State cannot be empty or whitespace only",
            field="state"
        )

    validate_text_length(state_clean, "State", min_length=2, max_length=100)

    # Optional: Validate against known states list
    if valid_states and state_clean not in valid_states:
        raise InvalidInputError(
            message=f"Invalid state: {state_clean}",
            field="state",
            details="Must be a valid Indian state or union territory"
        )


def validate_country(country: str) -> None:
    """
    Validate country name.

    Args:
        country: Country name

    Raises:
        InvalidInputError: If country is invalid
    """
    if not country:
        raise InvalidInputError(
            message="Country is required",
            field="country"
        )

    country_clean = country.strip()

    if not country_clean:
        raise InvalidInputError(
            message="Country cannot be empty or whitespace only",
            field="country"
        )

    validate_text_length(country_clean, "Country", min_length=2, max_length=100)


# ============================================================================
# BATCH VALIDATION
# ============================================================================

def validate_report_data(
    title: str,
    location: str,
    description: Optional[str] = None,
    username: Optional[str] = None
) -> Tuple[float, float]:
    """
    Validate all report data at once.

    Args:
        title: Report title
        location: Location string "lat,lng"
        description: Optional description
        username: Optional username

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        InvalidInputError: If any field is invalid
        InvalidCoordinatesError: If location is invalid
    """
    validate_report_title(title)

    if description:
        validate_report_description(description)

    if username:
        validate_username(username)

    lat, lng = parse_location_string(location)

    return lat, lng
