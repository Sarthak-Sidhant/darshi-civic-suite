"""
Security middleware and utilities for Darshi platform.
Includes rate limiting, input sanitization, and CORS configuration.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse
import bleach
from app.core.config import settings
from app.services import auth_service

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
    enabled=settings.RATE_LIMIT_ENABLED
)

# Custom rate limit handler
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors"""
    retry_after = getattr(exc, 'retry_after', None)

    # Build user-friendly message
    if retry_after:
        message = f"Rate limit exceeded. Please try again in {retry_after} seconds."
    else:
        message = "Rate limit exceeded. Please try again later."

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "detail": message,
            "message": message,
            "retry_after": retry_after,
            "recoverable": True
        }
    )

def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on user authentication status.
    Returns identifier for tiered rate limiting.
    """
    # Try to get user from Authorization header
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            # Verify token and get user
            payload = auth_service.verify_token(token)
            user_email = payload.get("email")
            user_role = payload.get("role", "citizen")

            # Return user email for authenticated rate limiting
            return f"user:{user_email}:{user_role}"
        except Exception:
            pass

    # Fall back to IP address for anonymous users
    return f"ip:{get_remote_address(request)}"

def get_user_tier(request: Request) -> str:
    """
    Determine user tier for rate limiting based on authentication and trust level.

    Tiers:
    - anonymous: No authentication
    - registered: Authenticated user
    - trusted: User with account >30 days old or >5 resolved reports
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return "anonymous"

    token = auth_header.split(" ")[1]
    try:
        payload = auth_service.verify_token(token)
        if payload is None:
            return "anonymous"

        # TODO: Implement trust level check based on:
        # - Account age (created_at)
        # - Number of resolved reports
        # For now, all authenticated users are "registered"

        return "registered"
    except Exception:
        return "anonymous"

def sanitize_input(text: str, strip_tags: bool = True) -> str:
    """
    Sanitize user input to prevent XSS attacks.

    Args:
        text: Input string to sanitize
        strip_tags: If True, strips all HTML tags. If False, allows safe tags.

    Returns:
        Sanitized string
    """
    if not text:
        return text

    if strip_tags:
        # Strip all HTML tags
        return bleach.clean(text, tags=[], strip=True)
    else:
        # Allow only safe tags (for descriptions, comments)
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
        return bleach.clean(text, tags=allowed_tags, strip=True)

def sanitize_form_data(data: dict) -> dict:
    """
    Sanitize all string fields in form data.

    Args:
        data: Dictionary of form fields

    Returns:
        Dictionary with sanitized values
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Sanitize string fields
            if key in ['description', 'comment', 'admin_notes']:
                # Allow basic formatting for longer text fields
                sanitized[key] = sanitize_input(value, strip_tags=False)
            else:
                # Strip all tags for titles, names, etc.
                sanitized[key] = sanitize_input(value, strip_tags=True)
        else:
            # Keep non-string values as-is
            sanitized[key] = value

    return sanitized

# CORS origin validator for subnet support
def validate_cors_origin(origin: str, allowed_origins: list) -> bool:
    """
    Validate CORS origin including support for subnet patterns.

    Args:
        origin: Request origin (e.g., "http://10.0.0.5:8080")
        allowed_origins: List of allowed origin patterns

    Returns:
        True if origin is allowed
    """
    if origin in allowed_origins:
        return True

    # Check pattern matching (e.g., "http://10.0.0.*")
    for pattern in allowed_origins:
        if '*' in pattern:
            # Simple wildcard matching
            import re
            regex_pattern = pattern.replace('.', r'\.').replace('*', r'.*')
            if re.match(f"^{regex_pattern}$", origin):
                return True

    return False

# Rate limit configurations by tier
# Development mode uses 10x higher limits for testing
RATE_LIMITS_PRODUCTION = {
    "anonymous": {
        "reports": "3/hour",
        "api": "50/hour",
        "login": "10/hour"
    },
    "registered": {
        "reports": "10/hour",
        "api": "200/hour",
        "login": "20/hour"
    },
    "trusted": {
        "reports": "20/hour",
        "api": "500/hour",
        "login": "50/hour"
    }
}

RATE_LIMITS_DEVELOPMENT = {
    "anonymous": {
        "reports": "100/hour",
        "api": "1000/hour",
        "login": "100/hour"
    },
    "registered": {
        "reports": "500/hour",
        "api": "5000/hour",
        "login": "500/hour"
    },
    "trusted": {
        "reports": "1000/hour",
        "api": "10000/hour",
        "login": "1000/hour"
    }
}

# Select rate limits based on environment
RATE_LIMITS = RATE_LIMITS_DEVELOPMENT if settings.ENVIRONMENT == "development" else RATE_LIMITS_PRODUCTION

# Development mode multiplier for endpoint-specific limits
DEV_RATE_MULTIPLIER = 10 if settings.ENVIRONMENT == "development" else 1


def dev_limit(limit: str) -> str:
    """
    Scale a rate limit string for development mode.
    E.g., "10/hour" becomes "100/hour" in development.
    """
    if settings.ENVIRONMENT != "development":
        return limit

    # Parse limit string like "10/hour" or "5/minute"
    try:
        parts = limit.split("/")
        count = int(parts[0])
        period = parts[1]
        return f"{count * DEV_RATE_MULTIPLIER}/{period}"
    except (ValueError, IndexError):
        return limit


def get_rate_limit(request: Request, limit_type: str = "api") -> str:
    """
    Get rate limit string based on user tier and limit type.

    Args:
        request: FastAPI request object
        limit_type: Type of limit ("reports", "api", "login")

    Returns:
        Rate limit string (e.g., "10/hour")
    """
    tier = get_user_tier(request)
    return RATE_LIMITS[tier][limit_type]
