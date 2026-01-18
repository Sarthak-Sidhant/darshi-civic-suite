"""
Error handling utilities for Darshi application.

Provides retry logic, circuit breakers, and error recovery mechanisms
for robust production operation.
"""

import time
from typing import Callable, Optional, Type, Tuple, Dict, Any
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from app.core.logging_config import get_logger
from app.core.exceptions import (
    DarshiBaseException,
    DatabaseTimeoutError,
    DatabaseConnectionError,
    StorageError,
    AIServiceError,
    AIRateLimitError,
    AITimeoutError,
    GeocodingError,
    GeocodingTimeoutError,
    AnalyticsError,
    AnalyticsTimeoutError,
    ExternalServiceError,
    ExternalServiceTimeoutError
)

logger = get_logger(__name__)


# ============================================================================
# CIRCUIT BREAKER IMPLEMENTATION
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold reached, requests fail fast
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying half-open
        expected_exception: Exception type to count as failures
        name: Identifier for logging
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        name: str = "CircuitBreaker"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == self.OPEN:
            if self._should_attempt_reset():
                self.state = self.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
            else:
                raise ExternalServiceError(
                    message=f"Circuit breaker '{self.name}' is OPEN",
                    service=self.name
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call."""
        if self.state == self.HALF_OPEN:
            self.state = self.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit breaker '{self.name}' recovered, state: CLOSED")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
            )


# Global circuit breakers for external services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Type[Exception] = Exception
) -> CircuitBreaker:
    """Get or create a circuit breaker for a service."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            name=name
        )
    return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: Type[Exception] = Exception
):
    """
    Decorator to apply circuit breaker pattern to a function.

    Usage:
        @circuit_breaker(name="gemini_api", failure_threshold=5)
        def call_gemini_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker(name, failure_threshold, recovery_timeout, expected_exception)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# RETRY DECORATORS
# ============================================================================

def retry_database_operation(max_attempts: int = 3):
    """
    Retry decorator for database operations.

    Retries on connection errors and timeouts with exponential backoff.
    """
    return retry(
        retry=retry_if_exception_type((
            DatabaseConnectionError,
            DatabaseTimeoutError,
            # Generic transient database errors
        )),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logger.level),
        after=after_log(logger, logger.level),
        reraise=True
    )


def retry_storage_operation(max_attempts: int = 2):
    """
    Retry decorator for storage operations.

    Retries on transient storage errors with exponential backoff.
    """
    return retry(
        retry=retry_if_exception_type(StorageError),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        before_sleep=before_sleep_log(logger, logger.level),
        after=after_log(logger, logger.level),
        reraise=True
    )


def retry_ai_operation(max_attempts: int = 3):
    """
    Retry decorator for AI service operations.

    Retries on rate limits and timeouts with exponential backoff.
    Special handling for rate limit errors (longer wait).
    """
    def should_retry(exception):
        if isinstance(exception, AIRateLimitError):
            # Longer wait for rate limits
            time.sleep(5)
            return True
        return isinstance(exception, (AITimeoutError, AIServiceError))

    return retry(
        retry=retry_if_exception_type((AIRateLimitError, AITimeoutError, AIServiceError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        before_sleep=before_sleep_log(logger, logger.level),
        after=after_log(logger, logger.level),
        reraise=True
    )


def retry_external_api(max_attempts: int = 3):
    """
    Retry decorator for external API calls (geocoding, etc).

    Retries on timeouts and transient errors with exponential backoff.
    """
    return retry(
        retry=retry_if_exception_type((
            GeocodingTimeoutError,
            GeocodingError,
            ExternalServiceTimeoutError,
            ExternalServiceError
        )),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logger.level),
        after=after_log(logger, logger.level),
        reraise=True
    )


def retry_analytics_query(max_attempts: int = 2):
    """
    Retry decorator for analytics queries.

    Retries on timeouts with exponential backoff.
    """
    return retry(
        retry=retry_if_exception_type((AnalyticsTimeoutError, AnalyticsError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=5, max=30),
        before_sleep=before_sleep_log(logger, logger.level),
        after=after_log(logger, logger.level),
        reraise=True
    )


# ============================================================================
# ERROR RECOVERY HELPERS
# ============================================================================

def safe_execute(
    func: Callable,
    fallback_value: Any = None,
    error_message: str = "Operation failed",
    log_level: str = "error",
    raise_on_failure: bool = False,
    expected_exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Any:
    """
    Safely execute a function with error handling and fallback.

    Args:
        func: Function to execute
        fallback_value: Value to return on failure
        error_message: Message to log on error
        log_level: Logging level ('error', 'warning', 'info')
        raise_on_failure: Whether to re-raise exceptions
        expected_exceptions: Exception types to catch

    Returns:
        Function result or fallback value
    """
    try:
        return func()
    except expected_exceptions as e:
        log_func = getattr(logger, log_level, logger.error)
        log_func(f"{error_message}: {e}", exc_info=True)

        if raise_on_failure:
            raise

        return fallback_value


def handle_service_error(
    error: Exception,
    operation: str,
    service: str,
    fallback_value: Any = None,
    raise_custom: bool = True
) -> Any:
    """
    Handle service errors with proper logging and exception mapping.

    Args:
        error: Original exception
        operation: Operation being performed
        service: Service name
        fallback_value: Value to return if not raising
        raise_custom: Whether to raise custom exception

    Returns:
        Fallback value if not raising

    Raises:
        DarshiBaseException: Mapped custom exception
    """
    logger.error(
        f"{service} error during {operation}: {error}",
        exc_info=True,
        extra={"service": service, "operation": operation}
    )

    if raise_custom:
        # Map to custom exception if not already
        if not isinstance(error, DarshiBaseException):
            raise ExternalServiceError(
                message=f"{service} operation failed: {operation}",
                service=service,
                details=str(error)
            ) from error
        raise

    return fallback_value


def validate_and_execute(
    func: Callable,
    validators: list[Callable[[Any], Tuple[bool, Optional[str]]]],
    *args,
    **kwargs
) -> Any:
    """
    Validate inputs before executing a function.

    Args:
        func: Function to execute
        validators: List of validation functions returning (is_valid, error_message)
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function result

    Raises:
        ValidationError: If validation fails
    """
    from app.core.exceptions import ValidationError

    for validator in validators:
        is_valid, error_message = validator(*args, **kwargs)
        if not is_valid:
            raise ValidationError(message=error_message)

    return func(*args, **kwargs)


# ============================================================================
# TIMEOUT HELPERS
# ============================================================================

class TimeoutError(Exception):
    """Raised when operation times out."""
    pass


def with_timeout(timeout_seconds: int, error_message: str = "Operation timed out"):
    """
    Decorator to add timeout to synchronous operations.

    Note: This uses a simple approach. For production, consider using
    asyncio timeouts for async operations or more sophisticated approaches.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(error_message)

            # Set the signal handler and alarm
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm and restore old handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper
    return decorator


# ============================================================================
# ERROR CONTEXT MANAGER
# ============================================================================

class ErrorContext:
    """
    Context manager for structured error handling.

    Usage:
        with ErrorContext("database", "create_report"):
            # database operations
    """

    def __init__(
        self,
        service: str,
        operation: str,
        error_class: Type[DarshiBaseException] = DarshiBaseException,
        raise_on_exit: bool = True,
        **extra_context
    ):
        self.service = service
        self.operation = operation
        self.error_class = error_class
        self.raise_on_exit = raise_on_exit
        self.extra_context = extra_context
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.debug(
            f"Starting {self.service}.{self.operation}",
            extra={"service": self.service, "operation": self.operation}
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is None:
            logger.debug(
                f"Completed {self.service}.{self.operation} in {duration:.2f}s",
                extra={
                    "service": self.service,
                    "operation": self.operation,
                    "duration": duration
                }
            )
            return True

        logger.error(
            f"Failed {self.service}.{self.operation} after {duration:.2f}s: {exc_val}",
            exc_info=True,
            extra={
                "service": self.service,
                "operation": self.operation,
                "duration": duration,
                "error_type": exc_type.__name__,
                **self.extra_context
            }
        )

        if self.raise_on_exit and not isinstance(exc_val, DarshiBaseException):
            # Convert to custom exception
            raise self.error_class(
                message=f"{self.service} operation failed: {self.operation}",
                details=str(exc_val),
                **self.extra_context
            ) from exc_val

        return not self.raise_on_exit
