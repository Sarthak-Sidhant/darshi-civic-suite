"""
PostgreSQL Analytics Service - Hotspot detection and analytics

This module provides analytics operations using PostgreSQL.
Replaces BigQuery with self-hosted PostgreSQL analytics queries.

Architecture:
- Async PostgreSQL queries for hotspot detection
- Geohash-based clustering for location analysis
- 5-minute cache for performance
- Graceful degradation on errors
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from app.services.postgres_service import get_db_connection
from app.core.exceptions import (
    AnalyticsError,
    AnalyticsServiceUnavailableError,
    AnalyticsQueryError,
    AnalyticsTimeoutError
)
from app.core.error_handling import retry_analytics_query, ErrorContext

logger = logging.getLogger(__name__)

# In-memory cache for hotspot alerts
# Cache TTL: 5 minutes (300 seconds) - balances freshness with performance
_alerts_cache = {
    "data": [],
    "timestamp": 0
}
_cache_lock = asyncio.Lock()
CACHE_TTL = 300  # 5 minutes


async def _get_cached_alerts() -> Optional[List[dict]]:
    """
    Check if cached alerts are still valid.

    Returns:
        Cached alerts if valid, None otherwise
    """
    async with _cache_lock:
        if _alerts_cache["data"] is not None:
            age = time.time() - _alerts_cache["timestamp"]
            if age < CACHE_TTL:
                logger.debug(f"Returning cached hotspot alerts (age: {age:.1f}s)")
                return _alerts_cache["data"]
    return None


async def _set_cached_alerts(alerts: List[dict]):
    """Store alerts in cache."""
    async with _cache_lock:
        _alerts_cache["data"] = alerts
        _alerts_cache["timestamp"] = time.time()
        logger.debug(f"Cached {len(alerts)} hotspot alerts for {CACHE_TTL}s")


async def get_hotspot_alerts() -> List[dict]:
    """
    Identify high-priority zones where multiple severe issues have been reported recently.

    Algorithm:
    - Find reports from last 24 hours with high/critical severity
    - Group by geohash prefix (6 chars = ~1.2km x 610m area)
    - Return areas with 3+ severe reports
    - Include category breakdown for context

    Results are cached for 5 minutes to reduce database load.

    Returns:
        List of hotspot alert dictionaries with structure:
        {
            "location": {"latitude": float, "longitude": float, "geohash_prefix": str},
            "report_count": int,
            "categories": list[str],
            "report_ids": list[str],
            "severity": "CRITICAL"
        }

    Raises:
        AnalyticsError: If query fails
        AnalyticsServiceUnavailableError: If PostgreSQL is unavailable
        AnalyticsTimeoutError: If query times out
    """
    # Check cache first - returns immediately if valid cache exists
    cached = await _get_cached_alerts()
    if cached is not None:
        return cached

    with ErrorContext("analytics", "get_hotspot_alerts", AnalyticsError, raise_on_exit=False):
        logger.debug("Fetching hotspot alerts from PostgreSQL")

        try:
            async with get_db_connection() as conn:
                # Calculate cutoff time (24 hours ago)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

                # Query to find hotspots via geohash clustering
                rows = await conn.fetch("""
                    WITH recent_severe AS (
                        SELECT
                            id,
                            title,
                            category,
                            severity,
                            latitude,
                            longitude,
                            geohash,
                            created_at,
                            SUBSTRING(geohash, 1, 6) as geohash_prefix
                        FROM reports
                        WHERE created_at >= $1
                          AND severity IN ('high', 'critical')
                          AND status IN ('VERIFIED', 'IN_PROGRESS', 'PENDING_VERIFICATION')
                    ),
                    hotspot_candidates AS (
                        SELECT
                            geohash_prefix,
                            COUNT(*) as report_count,
                            AVG(latitude) as avg_latitude,
                            AVG(longitude) as avg_longitude,
                            array_agg(DISTINCT category) as categories,
                            array_agg(id::text) as report_ids
                        FROM recent_severe
                        GROUP BY geohash_prefix
                        HAVING COUNT(*) >= 3
                    )
                    SELECT * FROM hotspot_candidates
                    ORDER BY report_count DESC
                    LIMIT 10
                """, cutoff_time)

                # Format results
                hotspots = []
                for row in rows:
                    hotspots.append({
                        "location": {
                            "latitude": float(row['avg_latitude']),
                            "longitude": float(row['avg_longitude']),
                            "geohash_prefix": row['geohash_prefix']
                        },
                        "report_count": row['report_count'],
                        "categories": list(set(row['categories'])),  # Unique categories
                        "report_ids": row['report_ids'],
                        "severity": "CRITICAL"
                    })

                if len(hotspots) == 0:
                    logger.info("No hotspot alerts detected (no areas with 3+ severe issues in last 24h)")
                else:
                    locations = [f"{h['location']['geohash_prefix']}" for h in hotspots]
                    logger.info(f"Detected {len(hotspots)} hotspot alert(s) in: {', '.join(locations)}")

                # Cache the results
                await _set_cached_alerts(hotspots)
                return hotspots

        except asyncio.TimeoutError as e:
            logger.error("Hotspot detection query timed out", exc_info=True)
            raise AnalyticsTimeoutError(
                message="Hotspot query timed out",
                query="hotspot_detection"
            ) from e

        except Exception as e:
            logger.error(f"Analytics query error: {e}", exc_info=True)
            # Graceful degradation - return empty list
            # Cache empty result to avoid repeated failed queries
            await _set_cached_alerts([])
            return []


async def get_report_statistics(time_window_hours: int = 24) -> Dict[str, any]:
    """
    Get aggregate report statistics for a time window.

    Args:
        time_window_hours: Hours to look back (default: 24)

    Returns:
        Dictionary with statistics:
        {
            "total_reports": int,
            "by_status": dict,
            "by_category": dict,
            "by_severity": dict,
            "avg_resolution_time_hours": float
        }
    """
    with ErrorContext("analytics", "get_report_statistics", AnalyticsError, raise_on_exit=False):
        try:
            async with get_db_connection() as conn:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

                # Get basic counts
                total = await conn.fetchval("""
                    SELECT COUNT(*) FROM reports WHERE created_at >= $1
                """, cutoff_time)

                # Group by status
                status_rows = await conn.fetch("""
                    SELECT status, COUNT(*) as count
                    FROM reports
                    WHERE created_at >= $1
                    GROUP BY status
                    ORDER BY count DESC
                """, cutoff_time)

                # Group by category
                category_rows = await conn.fetch("""
                    SELECT category, COUNT(*) as count
                    FROM reports
                    WHERE created_at >= $1
                    GROUP BY category
                    ORDER BY count DESC
                """, cutoff_time)

                # Group by severity
                severity_rows = await conn.fetch("""
                    SELECT severity, COUNT(*) as count
                    FROM reports
                    WHERE created_at >= $1
                    GROUP BY severity
                    ORDER BY count DESC
                """, cutoff_time)

                # Calculate average resolution time (for resolved reports)
                avg_resolution = await conn.fetchval("""
                    SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
                    FROM reports
                    WHERE created_at >= $1
                      AND status = 'RESOLVED'
                      AND resolved_at IS NOT NULL
                """, cutoff_time)

                return {
                    "total_reports": total or 0,
                    "by_status": {row['status']: row['count'] for row in status_rows},
                    "by_category": {row['category']: row['count'] for row in category_rows},
                    "by_severity": {row['severity']: row['count'] for row in severity_rows},
                    "avg_resolution_time_hours": round(avg_resolution, 2) if avg_resolution else None
                }

        except Exception as e:
            logger.error(f"Failed to get report statistics: {e}", exc_info=True)
            # Return empty stats on error
            return {
                "total_reports": 0,
                "by_status": {},
                "by_category": {},
                "by_severity": {},
                "avg_resolution_time_hours": None
            }


async def get_user_statistics() -> Dict[str, any]:
    """
    Get aggregate user statistics.

    Returns:
        Dictionary with user statistics:
        {
            "total_users": int,
            "active_users_24h": int,
            "top_contributors": list
        }
    """
    with ErrorContext("analytics", "get_user_statistics", AnalyticsError, raise_on_exit=False):
        try:
            async with get_db_connection() as conn:
                # Total users
                total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

                # Active users in last 24h (users who submitted reports)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                active_users = await conn.fetchval("""
                    SELECT COUNT(DISTINCT submitted_by)
                    FROM reports
                    WHERE created_at >= $1
                """, cutoff_time)

                # Top 10 contributors by report count
                top_contributors = await conn.fetch("""
                    SELECT username, reports_count, upvotes_received
                    FROM users
                    WHERE reports_count > 0
                    ORDER BY reports_count DESC
                    LIMIT 10
                """)

                return {
                    "total_users": total_users or 0,
                    "active_users_24h": active_users or 0,
                    "top_contributors": [
                        {
                            "username": row['username'],
                            "reports_count": row['reports_count'],
                            "upvotes_received": row['upvotes_received']
                        }
                        for row in top_contributors
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}", exc_info=True)
            return {
                "total_users": 0,
                "active_users_24h": 0,
                "top_contributors": []
            }
