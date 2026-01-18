"""
Shared HTTP Client

Provides a singleton httpx.AsyncClient with connection pooling for better performance.
Reduces overhead from creating/destroying connections for each API call.
"""

import httpx
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Singleton client instance
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Get or create singleton httpx.AsyncClient with optimized settings.

    Connection pooling benefits:
    - Reuses TCP connections across requests
    - Reduces latency from TCP handshake
    - Reduces server load from connection setup
    - Automatic connection lifecycle management

    Returns:
        httpx.AsyncClient instance with connection pooling
    """
    global _http_client

    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),  # 30s total, 10s connect
            limits=httpx.Limits(
                max_connections=100,  # Max total connections
                max_keepalive_connections=20,  # Keep 20 connections alive
                keepalive_expiry=30.0  # Keep connections alive for 30s
            ),
            follow_redirects=True,
            http2=True  # Enable HTTP/2 for better performance
        )
        logger.debug("HTTP client initialized with connection pooling")

    return _http_client


async def close_http_client():
    """
    Close HTTP client and cleanup connections.
    Should be called on application shutdown.
    """
    global _http_client

    if _http_client:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")
