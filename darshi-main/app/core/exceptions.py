"""
Custom exception classes for Darshi application.

Provides specific exception types for different service failures, enabling
granular error handling and appropriate recovery strategies.
"""

from typing import Optional, Dict, Any
from datetime import datetime


class DarshiBaseException(Exception):
    """
    Base exception class for all Darshi custom exceptions.

    Attributes:
        message: Human-readable error message
        code: Error code for categorization
        details: Additional context about the error
        timestamp: When the error occurred
        recoverable: Whether the error can be retried
    """

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[str] = None,
        recoverable: bool = False,
        **kwargs
    ):
        self.message = message
        self.code = code
        self.details = details
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow().isoformat()
        self.extra = kwargs
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp,
                "recoverable": self.recoverable,
                **self.extra
            }
        }


class RateLimitError(DarshiBaseException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message=message, code="RATE_LIMIT_ERROR", recoverable=False, **kwargs)


# Alias for backward compatibility
NotFoundError = DocumentNotFoundError if "DocumentNotFoundError" in locals() else None


# ============================================================================
# DATABASE ERRORS
# ============================================================================

class DatabaseError(DarshiBaseException):
    """Base class for all database-related errors."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        collection: Optional[str] = None,
        document_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            recoverable=True,
            operation=operation,
            collection=collection,
            document_id=document_id,
            **kwargs
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, message: str = "Failed to connect to database", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "DATABASE_CONNECTION_ERROR"


class DatabaseTimeoutError(DatabaseError):
    """Raised when database operation times out."""

    def __init__(self, message: str = "Database operation timed out", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "DATABASE_TIMEOUT_ERROR"


class DocumentNotFoundError(DatabaseError):
    """Raised when a requested document doesn't exist."""

    def __init__(self, message: str = "Document not found", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "DOCUMENT_NOT_FOUND"
        self.recoverable = False


class DocumentAlreadyExistsError(DatabaseError):
    """Raised when attempting to create a document that already exists."""

    def __init__(self, message: str = "Document already exists", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "DOCUMENT_ALREADY_EXISTS"
        self.recoverable = False


class TransactionError(DatabaseError):
    """Raised when a database transaction fails."""

    def __init__(self, message: str = "Transaction failed", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "TRANSACTION_ERROR"


# ============================================================================
# STORAGE ERRORS
# ============================================================================

class StorageError(DarshiBaseException):
    """Base class for all storage-related errors."""

    def __init__(
        self,
        message: str,
        bucket: Optional[str] = None,
        filename: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            recoverable=True,
            bucket=bucket,
            filename=filename,
            **kwargs
        )


class StorageConnectionError(StorageError):
    """Raised when storage service connection fails."""

    def __init__(self, message: str = "Failed to connect to storage service", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "STORAGE_CONNECTION_ERROR"


class StorageUploadError(StorageError):
    """Raised when file upload fails."""

    def __init__(self, message: str = "Failed to upload file", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "STORAGE_UPLOAD_ERROR"


class StorageDownloadError(StorageError):
    """Raised when file download fails."""

    def __init__(self, message: str = "Failed to download file", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "STORAGE_DOWNLOAD_ERROR"


class BucketNotFoundError(StorageError):
    """Raised when storage bucket doesn't exist."""

    def __init__(self, message: str = "Storage bucket not found", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "BUCKET_NOT_FOUND"


class StorageQuotaExceededError(StorageError):
    """Raised when storage quota is exceeded."""

    def __init__(self, message: str = "Storage quota exceeded", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "STORAGE_QUOTA_EXCEEDED"
        self.recoverable = False


# ============================================================================
# AI SERVICE ERRORS
# ============================================================================

class AIServiceError(DarshiBaseException):
    """Base class for all AI service-related errors."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="AI_SERVICE_ERROR",
            recoverable=True,
            model=model,
            **kwargs
        )


class AIServiceUnavailableError(AIServiceError):
    """Raised when AI service is unavailable."""

    def __init__(self, message: str = "AI service unavailable", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "AI_SERVICE_UNAVAILABLE"


class AIRateLimitError(AIServiceError):
    """Raised when AI service rate limit is exceeded."""

    def __init__(self, message: str = "AI service rate limit exceeded", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "AI_RATE_LIMIT_ERROR"


class AIQuotaExceededError(AIServiceError):
    """Raised when AI service quota is exceeded."""

    def __init__(self, message: str = "AI service quota exceeded", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "AI_QUOTA_EXCEEDED"
        self.recoverable = False


class AITimeoutError(AIServiceError):
    """Raised when AI service request times out."""

    def __init__(self, message: str = "AI service request timed out", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "AI_TIMEOUT_ERROR"


class AIInvalidResponseError(AIServiceError):
    """Raised when AI service returns invalid response."""

    def __init__(self, message: str = "AI service returned invalid response", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "AI_INVALID_RESPONSE"


# ============================================================================
# GEOCODING ERRORS
# ============================================================================

class GeocodingError(DarshiBaseException):
    """Base class for all geocoding-related errors."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="GEOCODING_ERROR",
            recoverable=True,
            query=query,
            latitude=latitude,
            longitude=longitude,
            **kwargs
        )


class GeocodingServiceUnavailableError(GeocodingError):
    """Raised when geocoding service is unavailable."""

    def __init__(self, message: str = "Geocoding service unavailable", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "GEOCODING_SERVICE_UNAVAILABLE"


class GeocodingTimeoutError(GeocodingError):
    """Raised when geocoding request times out."""

    def __init__(self, message: str = "Geocoding request timed out", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "GEOCODING_TIMEOUT_ERROR"


class InvalidCoordinatesError(GeocodingError):
    """Raised when coordinates are invalid."""

    def __init__(self, message: str = "Invalid coordinates", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INVALID_COORDINATES"
        self.recoverable = False


class GeohashError(GeocodingError):
    """Raised when geohash encoding fails."""

    def __init__(self, message: str = "Geohash encoding failed", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "GEOHASH_ERROR"


# ============================================================================
# ANALYTICS ERRORS
# ============================================================================

class AnalyticsError(DarshiBaseException):
    """Base class for all analytics-related errors."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="ANALYTICS_ERROR",
            recoverable=True,
            query=query,
            **kwargs
        )


class AnalyticsServiceUnavailableError(AnalyticsError):
    """Raised when analytics service is unavailable."""

    def __init__(self, message: str = "Analytics service unavailable", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "ANALYTICS_SERVICE_UNAVAILABLE"


class AnalyticsQueryError(AnalyticsError):
    """Raised when analytics query fails."""

    def __init__(self, message: str = "Analytics query failed", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "ANALYTICS_QUERY_ERROR"


class AnalyticsTimeoutError(AnalyticsError):
    """Raised when analytics query times out."""

    def __init__(self, message: str = "Analytics query timed out", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "ANALYTICS_TIMEOUT_ERROR"


class AnalyticsQuotaExceededError(AnalyticsError):
    """Raised when analytics quota is exceeded."""

    def __init__(self, message: str = "Analytics quota exceeded", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "ANALYTICS_QUOTA_EXCEEDED"
        self.recoverable = False


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(DarshiBaseException):
    """Base class for all validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            recoverable=False,
            field=field,
            **kwargs
        )
        # Don't include actual value in error for security
        if value is not None:
            self.extra['value_type'] = type(value).__name__


class InvalidInputError(ValidationError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Invalid input", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INVALID_INPUT"


class InvalidFileError(ValidationError):
    """Raised when file validation fails."""

    def __init__(self, message: str = "Invalid file", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INVALID_FILE"


class FileSizeExceededError(ValidationError):
    """Raised when file size exceeds limit."""

    def __init__(self, message: str = "File size exceeded", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "FILE_SIZE_EXCEEDED"


class InvalidFileTypeError(ValidationError):
    """Raised when file type is not allowed."""

    def __init__(self, message: str = "Invalid file type", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INVALID_FILE_TYPE"


# ============================================================================
# AUTHENTICATION ERRORS
# ============================================================================

class AuthenticationError(DarshiBaseException):
    """Base class for all authentication errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            recoverable=False,
            **kwargs
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid credentials", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""

    def __init__(self, message: str = "Token expired", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    """Raised when authentication token is invalid."""

    def __init__(self, message: str = "Invalid token", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INVALID_TOKEN"


class InsufficientPermissionsError(AuthenticationError):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "INSUFFICIENT_PERMISSIONS"


# ============================================================================
# EXTERNAL SERVICE ERRORS
# ============================================================================

class ExternalServiceError(DarshiBaseException):
    """Base class for external service errors."""

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            recoverable=True,
            service=service,
            status_code=status_code,
            **kwargs
        )


class ExternalServiceUnavailableError(ExternalServiceError):
    """Raised when external service is unavailable."""

    def __init__(self, message: str = "External service unavailable", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "EXTERNAL_SERVICE_UNAVAILABLE"


class ExternalServiceTimeoutError(ExternalServiceError):
    """Raised when external service request times out."""

    def __init__(self, message: str = "External service timeout", **kwargs):
        super().__init__(message=message, **kwargs)
        self.code = "EXTERNAL_SERVICE_TIMEOUT"


class EmailError(ExternalServiceError):
    """Raised when email service fails."""

    def __init__(self, message: str = "Email service error", **kwargs):
        super().__init__(message=message, service="email", **kwargs)
        self.code = "EMAIL_ERROR"
