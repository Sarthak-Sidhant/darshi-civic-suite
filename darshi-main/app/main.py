from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from app.routers import reports, admin, auth, oauth, users, notifications, location, municipality, public, user_alerts, flags, audit, cities, alerts, webhooks

from app.services import postgres_service
from app.core.config import settings
from app.core.security import limiter, rate_limit_exceeded_handler
from app.core.logging_config import setup_logging, get_logger
from app.core.redis_client import get_redis_client, close_redis_client
from app.core.http_client import close_http_client
from app.middleware import PerformanceMonitoringMiddleware
from app.core.exceptions import (
    DarshiBaseException,
    DatabaseError,
    StorageError,
    AIServiceError,
    GeocodingError,
    AnalyticsError,
    ValidationError,
    AuthenticationError
)
import uuid
from datetime import datetime

# Setup logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE,
    enable_sentry=settings.ENABLE_SENTRY,
    sentry_dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT
)

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting Darshi backend in {settings.ENVIRONMENT} mode")

    # Initialize PostgreSQL connection pool
    try:
        await postgres_service.get_db_pool()
        logger.info("✅ PostgreSQL connection pool initialized")
    except Exception as e:
        logger.critical(f"❌ Failed to initialize PostgreSQL: {e}")
        raise

    # Initialize Redis client if configured
    if settings.REDIS_URL:
        logger.info("Redis URL configured, initializing client...")
        client = get_redis_client()
        if client:
            logger.info("✅ Redis client connected successfully")
        else:
            logger.warning("⚠️ Redis client failed to connect, using in-memory fallback")
    else:
        logger.info("No Redis URL configured, using in-memory storage for rate limiting")

    yield

    # Shutdown
    logger.info("Shutting down Darshi backend...")
    await postgres_service.close_db_pool()
    logger.info("✅ PostgreSQL connection pool closed")
    close_redis_client()
    await close_http_client()
    logger.info("✅ All connections closed")

app = FastAPI(
    title="Darshi - Civic Grievance Platform",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ============================================================================
# GLOBAL EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(DarshiBaseException)
async def darshi_exception_handler(request: Request, exc: DarshiBaseException):
    """
    Handle all Darshi custom exceptions with structured error responses.
    """
    request_id = str(uuid.uuid4())

    logger.error(
        f"Request {request_id} failed with {exc.__class__.__name__}: {exc.message}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "path": request.url.path,
            "method": request.method
        }
    )

    # Map exception types to HTTP status codes
    status_code_map = {
        DatabaseError: 500,
        StorageError: 500,
        AIServiceError: 500,
        GeocodingError: 500,
        AnalyticsError: 500,
        ValidationError: 400,
        AuthenticationError: 401,
    }

    # Find the appropriate status code
    status_code = 500
    for exc_class, code in status_code_map.items():
        if isinstance(exc, exc_class):
            status_code = code
            break

    # Build error response
    error_response = exc.to_dict()
    error_response["error"]["request_id"] = request_id
    error_response["error"]["path"] = request.url.path

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI request validation errors.
    """
    request_id = str(uuid.uuid4())

    logger.warning(
        f"Request {request_id} validation failed: {exc.errors()}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "path": request.url.path
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected exceptions.
    """
    request_id = str(uuid.uuid4())

    logger.critical(
        f"Request {request_id} failed with unhandled exception: {exc}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )

    # Don't expose internal error details in production
    error_message = "An unexpected error occurred"
    if settings.ENVIRONMENT == "development":
        error_message = f"Internal server error: {str(exc)}"

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "path": request.url.path,
                "recoverable": False
            }
        }
    )

# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforce maximum request body size to prevent resource exhaustion.
    Limits all request bodies to 20MB by default.
    """
    async def dispatch(self, request: Request, call_next):
        # Check Content-Length header if present
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            max_size = 20 * 1024 * 1024  # 20MB
            if content_length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request body too large. Maximum size is 20MB, received {content_length / (1024*1024):.2f}MB",
                            "details": "Reduce the size of your request and try again",
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                    }
                )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses for defense-in-depth.

    Headers added:
    - X-Content-Type-Options: Prevent MIME-sniffing attacks
    - X-Frame-Options: Prevent clickjacking attacks
    - X-XSS-Protection: Enable XSS filtering in older browsers
    - Strict-Transport-Security: Force HTTPS connections
    - Content-Security-Policy: Prevent XSS and code injection
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME-sniffing (forces browser to respect Content-Type)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking (disallow embedding in iframes)
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter in older browsers (legacy but harmless)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS for 1 year (only in production)
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy: restrict resource loading
        # For /docs and /redoc, allow CDN resources for Swagger UI
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data: https://cdn.jsdelivr.net; "
                "connect-src 'self'"
            )
        else:
            # Stricter CSP for other endpoints
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'"
            )

        return response

# Add body size limit middleware (first, before other processing)
app.add_middleware(BodySizeLimitMiddleware)

# Add session middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="darshi_session",
    max_age=3600,  # 1 hour
    same_site="lax",
    https_only=settings.ENVIRONMENT == "production"
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add GZip compression for all responses > 500 bytes
# This reduces payload size by 60-80% for JSON responses
app.add_middleware(GZipMiddleware, minimum_size=500)

# Add monitoring middleware
app.add_middleware(PerformanceMonitoringMiddleware)
# Uncomment for detailed request/response logging (verbose)
# app.add_middleware(RequestLoggingMiddleware)

# Configure CORS with proper origins
# Parse origins from settings (supports subnet notation)
allowed_origins = []
for origin in settings.CORS_ORIGINS.split(","):
    origin = origin.strip()
    if "/24" in origin:
        # Handle subnet: expand to individual IPs or use pattern
        # For development, we'll allow all IPs in the subnet
        base = origin.split("/")[0].rsplit(".", 1)[0]
        # Add pattern for CORS matching (FastAPI CORSMiddleware supports regex)
        for i in range(1, 255):
            allowed_origins.append(f"http://{base}.{i}:5173")
            allowed_origins.append(f"http://{base}.{i}:8080")
            allowed_origins.append(f"http://{base}.{i}:3000")
    else:
        allowed_origins.append(origin)

# Add environment-specific origins
if settings.ENVIRONMENT == "development":
    allowed_origins.extend([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
        "http://10.0.0.43:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://10.0.0.43:8080",
    ])
elif settings.ENVIRONMENT == "production":
    # Ensure production domains are always included
    allowed_origins.extend([
        "https://darshi.app",
        "https://www.darshi.app",
        "https://api.darshi.app",
    ])

# Remove duplicates
allowed_origins = list(set(allowed_origins))

logger.info(f"CORS allowed origins ({settings.ENVIRONMENT}): {allowed_origins[:5]}... (showing first 5)")

# SECURITY: Validate CORS configuration in production
if settings.ENVIRONMENT == "production":
    if not allowed_origins or "*" in allowed_origins:
        raise RuntimeError(
            "CRITICAL SECURITY ERROR: CORS_ORIGINS must be explicitly configured in production. "
            "Wildcard origins (*) with credentials are not allowed. "
            "Set CORS_ORIGINS environment variable with your production domains."
        )

# SECURITY: Never allow wildcard origins with credentials
# If no origins configured, fail in production, allow localhost in development
if not allowed_origins:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("CORS_ORIGINS must be configured in production")
    else:
        logger.warning("No CORS origins configured, defaulting to localhost for development")
        allowed_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080"
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # NEVER use ["*"] fallback with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(location.router)
app.include_router(municipality.router)
app.include_router(public.router)
app.include_router(user_alerts.router)
app.include_router(flags.router, prefix="/api/v1")
app.include_router(audit.router)
app.include_router(cities.router)
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(webhooks.router)

@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks:
    - PostgreSQL (database connectivity)
    - Cloudflare R2 (storage service)
    - Gemini AI (ML service)
    - Redis (cache service)

    Returns:
        dict with overall status and individual service statuses
    """
    import time
    start_time = time.time()

    health_status = {
        "status": "healthy",
        "service": "Darshi Backend v2.0 (Self-Hosted)",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # 1. PostgreSQL Health Check
    try:
        async with postgres_service.get_db_connection() as conn:
            # Test query
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                health_status["checks"]["postgresql"] = {
                    "status": "healthy",
                    "message": "Connected and responsive"
                }
            else:
                health_status["checks"]["postgresql"] = {
                    "status": "unhealthy",
                    "message": "Query returned unexpected result"
                }
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["postgresql"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # 2. Cloudflare R2 Storage Health Check
    try:
        from app.services import storage_service
        # Check if bucket is configured and can be accessed
        if storage_service.BUCKET_NAME:
            # Get client (lazy initialization) and test bucket access
            client = storage_service.get_s3_client()
            client.head_bucket(Bucket=storage_service.BUCKET_NAME)
            health_status["checks"]["r2_storage"] = {
                "status": "healthy",
                "bucket": storage_service.BUCKET_NAME,
                "message": "Bucket accessible"
            }
        else:
            health_status["checks"]["r2_storage"] = {
                "status": "unhealthy",
                "message": "R2 bucket not configured"
            }
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["r2_storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # 3. Gemini AI Health Check
    try:
        from app.services import ai_service
        model = ai_service.get_gemini_model()
        if model:
            health_status["checks"]["gemini"] = {
                "status": "healthy",
                "model": "gemini-2.5-flash"
            }
        else:
            health_status["checks"]["gemini"] = {
                "status": "unavailable",
                "message": "Model not configured"
            }
    except Exception as e:
        health_status["checks"]["gemini"] = {
            "status": "degraded",
            "error": str(e)
        }

    # 4. Redis Health Check
    try:
        from app.core.redis_client import is_redis_available
        if is_redis_available():
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "message": "Connected and responsive"
            }
        else:
            health_status["checks"]["redis"] = {
                "status": "unavailable",
                "message": "Redis not configured or unreachable"
            }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "degraded",
            "error": str(e)
        }

    # Calculate response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

    # Determine overall HTTP status code
    status_code = 200
    if health_status["status"] == "degraded":
        status_code = 503
    elif health_status["status"] == "unhealthy":
        status_code = 503

    return JSONResponse(status_code=status_code, content=health_status)


@app.get("/ping")
def ping(client_timestamp: float = None):
    """
    Ping endpoint for latency testing.

    Usage:
    - GET /ping - Returns server timestamp and region
    - GET /ping?client_timestamp=1734567890.123 - Also calculates one-way latency

    For round-trip time, measure on client side:
        start = performance.now()
        fetch('/ping')
        rtt = performance.now() - start
    """
    import time
    server_time = time.time()

    response = {
        "pong": True,
        "server_timestamp": server_time,
        "region": "asia-southeast1"
    }

    if client_timestamp:
        # One-way latency (client → server) in milliseconds
        response["one_way_latency_ms"] = round((server_time - client_timestamp) * 1000, 2)

    return response
