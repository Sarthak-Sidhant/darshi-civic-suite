"""
Centralized logging configuration for Darshi.
Provides structured logging with proper log levels and optional Sentry integration.
"""
import logging
import sys
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_sentry: bool = False,
    sentry_dsn: Optional[str] = None,
    environment: str = "development"
) -> logging.Logger:
    """
    Setup centralized logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        enable_sentry: Whether to enable Sentry error tracking
        sentry_dsn: Sentry DSN for error tracking
        environment: Environment name (development, staging, production)

    Returns:
        Configured root logger
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Colored formatter for console
    console_format = '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s'
    console_formatter = ColoredFormatter(console_format, datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file

        # Standard formatter for file (no colors)
        file_format = '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s'
        file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Setup Sentry if enabled
    if enable_sentry and sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            from sentry_sdk.integrations.asyncio import AsyncioIntegration

            # Configure Sentry logging integration
            sentry_logging = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors and above as events
            )

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
                profiles_sample_rate=0.1,  # 10% for profiling
                integrations=[
                    sentry_logging,
                    AsyncioIntegration(),
                ],
                # Set before_send to filter sensitive data
                before_send=filter_sensitive_data,
            )

            root_logger.info("Sentry error tracking initialized")
        except ImportError:
            root_logger.warning("Sentry SDK not installed, error tracking disabled")
        except Exception as e:
            root_logger.error(f"Failed to initialize Sentry: {e}")

    return root_logger


def filter_sensitive_data(event, hint):
    """
    Filter sensitive data before sending to Sentry.
    Removes passwords, tokens, and other sensitive information.
    """
    # Remove sensitive headers
    if 'request' in event and 'headers' in event['request']:
        headers = event['request']['headers']
        sensitive_headers = ['authorization', 'x-admin-token', 'cookie']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'

    # Remove sensitive query parameters
    if 'request' in event and 'query_string' in event['request']:
        query = event['request']['query_string']
        if query and ('password' in query.lower() or 'token' in query.lower()):
            event['request']['query_string'] = '[Filtered]'

    return event


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
