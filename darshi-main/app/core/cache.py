"""
Redis Caching Utilities

Provides helper functions for caching with Redis.
Handles JSON serialization, TTL management, and cache invalidation.
"""

import json
from typing import Optional, Any, Callable
from functools import wraps
from app.core.redis_client import get_redis_client
from app.core.logging_config import get_logger
from app.core.config import settings

logger = get_logger(__name__)


def cache_get(key: str) -> Optional[Any]:
    """
    Get value from Redis cache.

    Args:
        key: Cache key

    Returns:
        Cached value (deserialized from JSON) or None if not found
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        value = client.get(key)
        if value:
            logger.debug(f"Cache hit: {key}")
            return json.loads(value)
        else:
            logger.debug(f"Cache miss: {key}")
            return None
    except Exception as e:
        logger.warning(f"Redis cache get error for key '{key}': {e}")
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set value in Redis cache with optional TTL.

    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        ttl: Time-to-live in seconds (default from settings.REDIS_CACHE_TTL)

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    ttl = ttl or settings.REDIS_CACHE_TTL

    try:
        serialized = json.dumps(value)
        client.setex(key, ttl, serialized)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Redis cache set error for key '{key}': {e}")
        return False


def cache_delete(key: str) -> bool:
    """
    Delete value from Redis cache.

    Args:
        key: Cache key

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.delete(key)
        logger.debug(f"Cache deleted: {key}")
        return True
    except Exception as e:
        logger.warning(f"Redis cache delete error for key '{key}': {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "geocode:*")

    Returns:
        Number of keys deleted
    """
    client = get_redis_client()
    if not client:
        return 0

    try:
        keys = list(client.scan_iter(match=pattern))
        if keys:
            deleted = client.delete(*keys)
            logger.debug(f"Cache pattern delete: {pattern} ({deleted} keys)")
            return deleted
        return 0
    except Exception as e:
        logger.warning(f"Redis cache pattern delete error for pattern '{pattern}': {e}")
        return 0


def cached(key_prefix: str, ttl: Optional[int] = None, key_builder: Optional[Callable] = None):
    """
    Decorator for caching function results in Redis.

    Args:
        key_prefix: Prefix for cache key (e.g., "geocode", "landmark")
        ttl: Time-to-live in seconds (default from settings.REDIS_CACHE_TTL)
        key_builder: Optional function to build cache key from args/kwargs
                    Signature: (args, kwargs) -> str
                    If not provided, uses repr of args/kwargs

    Example:
        @cached(key_prefix="geocode", ttl=300)
        async def geocode_address(query: str):
            # ...expensive operation...
            return results

        # Default key builder: "geocode:{'query': 'New York'}"

        @cached(key_prefix="landmark", key_builder=lambda args, kwargs: f"{args[0]},{args[1]}")
        async def get_landmark(lat: float, lng: float):
            # ...expensive operation...
            return landmark

        # Custom key builder: "landmark:40.7128,-74.0060"
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                key_suffix = key_builder(args, kwargs)
            else:
                # Default: use repr of args/kwargs
                key_suffix = repr((args, kwargs))

            cache_key = f"{key_prefix}:{key_suffix}"

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)

            # Only cache non-None results
            if result is not None:
                cache_set(cache_key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                key_suffix = key_builder(args, kwargs)
            else:
                key_suffix = repr((args, kwargs))

            cache_key = f"{key_prefix}:{key_suffix}"

            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = func(*args, **kwargs)

            # Only cache non-None results
            if result is not None:
                cache_set(cache_key, result, ttl)

            return result

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(key_prefix: str, *args, **kwargs):
    """
    Manually invalidate cache for a specific key.

    Args:
        key_prefix: Cache key prefix
        *args, **kwargs: Function arguments to build cache key

    Example:
        invalidate_cache("geocode", query="New York")
    """
    key_suffix = repr((args, kwargs))
    cache_key = f"{key_prefix}:{key_suffix}"
    cache_delete(cache_key)
