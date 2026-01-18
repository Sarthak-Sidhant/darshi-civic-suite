"""
Redis Client Configuration

Provides a singleton Redis client for caching, rate limiting, and task queues.
"""

import redis
from typing import Optional
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Singleton Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client singleton.

    Returns None if Redis is not configured.
    Auto-connects on first call if REDIS_URL is set.
    """
    global _redis_client

    # Return None if Redis not configured
    if not settings.REDIS_URL:
        return None

    # Initialize client if not already done
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,  # Return strings instead of bytes
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            _redis_client.ping()
            logger.info("Redis client connected successfully")

        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            _redis_client = None

    return _redis_client


def close_redis_client():
    """
    Close Redis connection.
    Called on application shutdown.
    """
    global _redis_client

    if _redis_client:
        try:
            _redis_client.close()
            logger.info("Redis client closed")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
        finally:
            _redis_client = None


def is_redis_available() -> bool:
    """
    Check if Redis is available.
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.ping()
        return True
    except:
        return False
