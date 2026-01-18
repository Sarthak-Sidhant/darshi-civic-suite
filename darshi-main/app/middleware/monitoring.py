"""
Performance monitoring middleware for tracking request metrics.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor request performance and log metrics.
    Tracks request duration, status codes, and identifies slow requests.
    """

    SLOW_REQUEST_THRESHOLD = 2.0  # seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for health checks and static files
        if request.url.path in ["/health", "/favicon.ico"]:
            return await call_next(request)

        # Start timer
        start_time = time.time()

        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log incoming request
        logger.debug(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception and re-raise
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "client_ip": client_ip,
                }
            )
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Add performance headers
        response.headers["X-Process-Time"] = str(duration)

        # Log request completion
        log_level = logger.info
        if response.status_code >= 500:
            log_level = logger.error
        elif response.status_code >= 400:
            log_level = logger.warning
        elif duration > self.SLOW_REQUEST_THRESHOLD:
            log_level = logger.warning

        log_level(
            f"Request completed: {request.method} {request.url.path} "
            f"[{response.status_code}] in {duration:.3f}s",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
                "client_ip": client_ip,
                "slow_request": duration > self.SLOW_REQUEST_THRESHOLD,
            }
        )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed request/response logging.
    Useful for debugging and audit trails.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request details
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        headers = dict(request.headers)

        # Filter sensitive headers
        sensitive_headers = ["authorization", "x-admin-token", "cookie"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"

        # Log request details (debug level)
        logger.debug(
            f"Request details: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_params": query_params,
                "headers": headers,
            }
        )

        # Process request
        response = await call_next(request)

        # Log response details (debug level)
        logger.debug(
            f"Response details: {method} {path} [{response.status_code}]",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "response_headers": dict(response.headers),
            }
        )

        return response
