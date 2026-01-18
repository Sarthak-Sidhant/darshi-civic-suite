"""
PostgreSQL Database Service - Complete replacement for Firestore db_service.py

This module provides all database operations using asyncpg for PostgreSQL.
Functions maintain API compatibility with the original Firestore implementation.

Architecture:
- Connection pooling for performance
- Async/await for all operations
- Atomic transactions for critical operations (upvotes, user creation)
- Structured error handling with context
"""

import asyncpg
import logging
import json
import pygeohash
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.exceptions import DatabaseError
from app.core.error_handling import retry_database_operation, ErrorContext

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """Get or create PostgreSQL connection pool."""
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                dsn=settings.ASYNC_DATABASE_URL,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'application_name': 'darshi_backend',
                    'timezone': 'UTC'
                }
            )
            logger.info("PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to initialize database connection pool",
                details=str(e),
                context={"operation": "pool_creation"}
            )
    return _pool


async def close_db_pool():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


@asynccontextmanager
async def get_db_connection():
    """Get a connection from the pool (context manager)."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn


async def get_db():
    """FastAPI dependency to get database connection."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _is_valid_geohash(geohash: str) -> bool:
    """Validate geohash format (copied from original db_service)."""
    if not geohash or not isinstance(geohash, str):
        return False
    if len(geohash) < 4 or len(geohash) > 12:
        return False
    valid_chars = set('0123456789bcdefghjkmnpqrstuvwxyz')
    return all(c in valid_chars for c in geohash.lower())


def _row_to_dict(row: asyncpg.Record) -> dict:
    """Convert asyncpg Record to dictionary."""
    if row is None:
        return None

    result = dict(row)

    # Convert datetime objects to ISO format strings
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()

    return result


def _rows_to_list(rows: List[asyncpg.Record]) -> List[dict]:
    """Convert list of asyncpg Records to list of dictionaries."""
    return [_row_to_dict(row) for row in rows]


# ============================================================================
# REPORT FUNCTIONS (15 functions)
# ============================================================================

# @retry_database_operation
async def create_report(data: dict) -> str:
    """
    Create a new report in PostgreSQL.

    Args:
        data: Report data dictionary

    Returns:
        str: Report ID (UUID)

    Raises:
        DatabaseError: If creation fails
    """
    with ErrorContext("database", "create_report"):
        try:
            async with get_db_connection() as conn:
                # Prepare data with defaults
                now = datetime.now(timezone.utc)

                # Calculate geohash if not provided
                if 'geohash' not in data and 'latitude' in data and 'longitude' in data:
                    data['geohash'] = pygeohash.encode(
                        float(data['latitude']),
                        float(data['longitude']),
                        precision=7
                    )

                # Initialize timeline with REPORT_CREATED event
                timeline = [{
                    "event": "REPORT_CREATED",
                    "timestamp": now.isoformat(),
                    "actor": data.get('submitted_by', 'system'),
                    "details": "Report submitted"
                }]

                # Insert report
                row = await conn.fetchrow("""
                    INSERT INTO reports (
                        title, description, category, severity,
                        latitude, longitude, geohash, location,
                        address, city, state, country,
                        status, image_urls, image_hash, dhash_bucket,
                        submitted_by, upvotes, upvote_count, comment_count,
                        ai_analysis, timeline, created_at, updated_at
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7, ST_SetSRID(ST_MakePoint($6, $5), 4326),
                        $8, $9, $10, $11,
                        $12, $13, $14, $15,
                        $16, $17, $18, $19,
                        $20, $21, $22, $22
                    ) RETURNING id
                """,
                    data.get('title'),
                    data.get('description'),
                    data.get('category'),
                    data.get('severity', 'medium'),
                    float(data.get('latitude')),
                    float(data.get('longitude')),
                    data.get('geohash'),
                    data.get('address', ''),
                    data.get('city', ''),
                    data.get('state', ''),
                    data.get('country', 'India'),
                    data.get('status', 'PENDING_VERIFICATION'),
                    data.get('image_urls', []),
                    data.get('image_hash'),
                    data.get('image_hash', '')[:4] if data.get('image_hash') else '',
                    data.get('submitted_by'),
                    data.get('upvotes', []),
                    data.get('upvote_count', 0),
                    data.get('comment_count', 0),
                    json.dumps(data.get('ai_analysis', {})),
                    json.dumps(timeline),
                    now
                )

                # Auto-assign municipality based on location (New Logic)
                try:
                    from app.services.location_service import location_service
                    # We do this asynchronously/inline because it's critical for routing
                    muni = await location_service.get_nearest_municipality(
                        float(data.get('latitude')), 
                        float(data.get('longitude'))
                    )
                    
                    if muni:
                        # Update the report we just created
                        # We do this as a separate update to keep the INSERT clean, 
                        # or we could move this logic before the INSERT.
                        # Doing it after allows us to not block if location service fails.
                        await conn.execute("""
                            UPDATE reports 
                            SET assigned_municipality = $1, assigned_at = $2
                            WHERE id = $3
                        """, muni['id'], now, row['id'])
                        
                        logger.info(f"Report {row['id']} auto-assigned to municipality: {muni['name']}")
                except Exception as loc_err:
                    logger.error(f"Failed to auto-assign municipality: {loc_err}")

                report_id = str(row['id'])
                logger.info(f"Report created: {report_id}")
                return report_id

        except Exception as e:
            logger.error(f"Failed to create report: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to create report",
                details=str(e),
                context={"operation": "create"}
            )


# @retry_database_operation
async def get_report_by_id(report_id: str) -> Optional[dict]:
    """
    Get report by ID.

    Args:
        report_id: Report UUID

    Returns:
        dict: Report data or None if not found
    """
    with ErrorContext("database", "get_report_by_id"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        id, title, description, category, severity,
                        latitude, longitude, geohash, location,
                        address, city, state, country,
                        status, image_urls, image_hash,
                        submitted_by, upvotes, upvote_count, comment_count,
                        ai_analysis, duplicate_of, timeline,
                        created_at, updated_at, verified_at, resolved_at
                    FROM reports
                    WHERE id = $1
                """, report_id)

                if row is None:
                    return None

                result = _row_to_dict(row)

                # Parse JSON fields
                if result.get('ai_analysis'):
                    result['ai_analysis'] = json.loads(result['ai_analysis'])
                if result.get('timeline'):
                    result['timeline'] = json.loads(result['timeline'])

                return result

        except Exception as e:
            logger.error(f"Failed to get report {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve report",
                details=str(e),
                context={"report_id": report_id}
            )


# @retry_database_operation
async def update_report(report_id: str, updates: dict) -> bool:
    """
    Update report fields.

    Args:
        report_id: Report UUID
        updates: Dictionary of fields to update

    Returns:
        bool: True if updated, False if not found
    """
    with ErrorContext("database", "update_report"):
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_count = 1

            for key, value in updates.items():
                # Skip fields that shouldn't be updated directly
                if key in ['id', 'created_at']:
                    continue

                # Handle JSON fields
                if key in ['ai_analysis', 'timeline']:
                    value = json.dumps(value)

                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

            # Always update updated_at
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.now(timezone.utc))
            param_count += 1

            # Add report_id as final parameter
            values.append(report_id)

            if not set_clauses:
                return False

            query = f"""
                UPDATE reports
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """

            async with get_db_connection() as conn:
                result = await conn.execute(query, *values)

                updated = result.split()[-1] == '1'
                if updated:
                    logger.info(f"Report updated: {report_id}")

                return updated

        except Exception as e:
            logger.error(f"Failed to update report {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to update report",
                details=str(e),
                context={"report_id": report_id}
            )


async def get_reports(
    limit: int = 20,
    start_after_id: Optional[str] = None,
    geohash: Optional[str] = None,
    current_user_id: Optional[str] = None,
    city_id: Optional[str] = None,
    district_code: Optional[int] = None,
    district_name: Optional[str] = None,
    state_name: Optional[str] = None
) -> List[dict]:
    """
    Get reports with pagination and flexible filtering.

    Args:
        limit: Maximum number of reports to return
        start_after_id: Cursor for pagination (report ID)
        geohash: Geohash prefix for location filtering
        current_user_id: Current user's username for has_upvoted field
        city_id: Filter by city ID
        district_code: Filter by LGD district code
        district_name: Filter by district name (text match)
        state_name: Filter by state name (with district_name)

    Returns:
        List[dict]: List of reports with has_upvoted field
    """
    with ErrorContext("database", "get_reports"):
        try:
            async with get_db_connection() as conn:
                where_clauses = ["r.status NOT IN ('REJECTED', 'FLAGGED')"]
                params = []
                param_count = 1

                # Add current_user_id as first param if provided (for has_upvoted check)
                if current_user_id:
                    user_id_param = param_count
                    params.append(current_user_id)
                    param_count += 1
                else:
                    user_id_param = None
                
                # City Filter
                if city_id:
                    where_clauses.append(f"r.city_id = ${param_count}")
                    params.append(city_id)
                    param_count += 1
                
                # District Filter - try code first, fall back to text
                if district_code:
                    # Check if district_code column exists
                    col_exists = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'reports' 
                            AND column_name = 'district_code'
                        )
                    """)
                    if col_exists:
                        where_clauses.append(f"r.district_code = ${param_count}")
                        params.append(district_code)
                        param_count += 1
                    else:
                        # Fallback: look up district name from districts table
                        district_info = await conn.fetchrow(
                            "SELECT district_name, state_name FROM districts WHERE district_code = $1",
                            district_code
                        )
                        if district_info:
                            where_clauses.append(f"LOWER(r.city) = LOWER(${param_count})")
                            params.append(district_info['district_name'])
                            param_count += 1
                            where_clauses.append(f"LOWER(r.state) = LOWER(${param_count})")
                            params.append(district_info['state_name'])
                            param_count += 1
                elif district_name:
                    where_clauses.append(f"LOWER(r.city) = LOWER(${param_count})")
                    params.append(district_name)
                    param_count += 1
                    if state_name:
                        where_clauses.append(f"LOWER(r.state) = LOWER(${param_count})")
                        params.append(state_name)
                        param_count += 1

                # Geohash filter
                if geohash and _is_valid_geohash(geohash):
                    where_clauses.append(f"r.geohash LIKE ${param_count}")
                    params.append(f"{geohash}%")
                    param_count += 1

                # Cursor pagination
                if start_after_id:
                    where_clauses.append(f"r.created_at < (SELECT created_at FROM reports WHERE id = ${param_count})")
                    params.append(start_after_id)
                    param_count += 1

                params.append(limit)

                # Build has_upvoted expression
                has_upvoted_expr = f"(${user_id_param} = ANY(r.upvotes))" if user_id_param else "false"

                query = f"""
                    SELECT
                        r.id, r.title, r.description, r.category, r.severity,
                        r.latitude, r.longitude, r.geohash,
                        r.address, r.city, r.state, r.country,
                        r.status, r.image_urls, r.image_hash,
                        r.submitted_by, r.upvote_count, r.comment_count,
                        {has_upvoted_expr} as has_upvoted,
                        r.ai_analysis, r.flag_reason,
                        r.created_at, r.updated_at,
                        officer.username as officer_username,
                        u.badges as user_badges,
                        u.role as user_role
                    FROM reports r
                    LEFT JOIN users u ON r.submitted_by = u.username
                    LEFT JOIN users officer ON r.assigned_by = officer.username
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY r.created_at DESC
                    LIMIT ${param_count}
                """
                
                rows = await conn.fetch(query, *params)
                results = _rows_to_list(rows)
                
                # Parse JSON fields for each report
                for r in results:
                    if r.get('ai_analysis') and isinstance(r['ai_analysis'], str):
                        try:
                            r['ai_analysis'] = json.loads(r['ai_analysis'])
                        except:
                            r['ai_analysis'] = None
                    # Ensure badges array
                    if r.get('user_badges') is None:
                        r['user_badges'] = []
                            
                return results

        except Exception as e:
            logger.error(f"Failed to get reports: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve reports",
                details=str(e),
                context={"limit": limit}
            )


async def get_reports_admin(
    limit: int = 20,
    start_after_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> List[dict]:
    """
    Get all reports (admin view with all statuses).

    Args:
        limit: Maximum number of reports
        start_after_id: Cursor for pagination
        status_filter: Optional status filter

    Returns:
        List[dict]: List of reports
    """
    with ErrorContext("database", "get_reports_admin"):
        try:
            async with get_db_connection() as conn:
                where_clauses = []
                params = []
                param_count = 1

                # Status filter
                if status_filter:
                    where_clauses.append(f"status = ${param_count}")
                    params.append(status_filter)
                    param_count += 1

                # Cursor pagination
                if start_after_id:
                    where_clauses.append(f"created_at < (SELECT created_at FROM reports WHERE id = ${param_count})")
                    params.append(start_after_id)
                    param_count += 1

                params.append(limit)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"""
                    SELECT
                        id, title, description, category, severity,
                        latitude, longitude, geohash, location,
                        address, city, state, country,
                        status, image_urls, image_hash,
                        submitted_by, upvote_count, comment_count,
                        ai_analysis, timeline,
                        created_at, updated_at, verified_at, resolved_at
                    FROM reports
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ${param_count}
                """

                rows = await conn.fetch(query, *params)
                results = _rows_to_list(rows)

                # Parse JSON fields
                for result in results:
                    if result.get('ai_analysis'):
                        result['ai_analysis'] = json.loads(result['ai_analysis'])
                    if result.get('timeline'):
                        result['timeline'] = json.loads(result['timeline'])

                return results

        except Exception as e:
            logger.error(f"Failed to get admin reports: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve admin reports",
                details=str(e)
            )


# @retry_database_operation
async def upvote_report(report_id: str, user_id: str) -> dict:
    """
    Upvote a report (atomic transaction to prevent race conditions).

    Args:
        report_id: Report UUID
        user_id: Username

    Returns:
        dict: {"count": int, "status": str, "error": Optional[str]}
    """
    with ErrorContext("database", "upvote_report"):
        try:
            async with get_db_connection() as conn:
                async with conn.transaction():
                    # Check if already upvoted and update atomically
                    row = await conn.fetchrow("""
                        UPDATE reports
                        SET
                            upvotes = array_append(upvotes, $2),
                            upvote_count = upvote_count + 1
                        WHERE id = $1
                          AND NOT ($2 = ANY(upvotes))
                        RETURNING upvote_count
                    """, report_id, user_id)

                    if row is None:
                        # Check if report exists
                        exists = await conn.fetchval(
                            "SELECT 1 FROM reports WHERE id = $1",
                            report_id
                        )

                        if not exists:
                            return {
                                "count": 0,
                                "status": "error",
                                "error": "Report not found"
                            }

                        # Already upvoted
                        current_count = await conn.fetchval(
                            "SELECT upvote_count FROM reports WHERE id = $1",
                            report_id
                        )

                        return {
                            "count": current_count,
                            "status": "already_upvoted",
                            "error": None
                        }

                    logger.info(f"Report {report_id} upvoted by {user_id}")

                    return {
                        "count": row['upvote_count'],
                        "status": "success",
                        "error": None
                    }

        except Exception as e:
            logger.error(f"Failed to upvote report {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to upvote report",
                details=str(e),
                context={"report_id": report_id, "user_id": user_id}
            )


# @retry_database_operation
async def add_timeline_event(
    report_id: str,
    title: str,
    description: str = "",
    actor: str = "system"
) -> None:
    """
    Add a timeline event to report (atomic append).

    Args:
        report_id: Report UUID
        title: Event title
        description: Event description
        actor: Username of actor
    """
    with ErrorContext("database", "add_timeline_event"):
        try:
            event = {
                "event": title,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "details": description
            }

            async with get_db_connection() as conn:
                await conn.execute("""
                    UPDATE reports
                    SET timeline = timeline || $2::jsonb
                    WHERE id = $1
                """, report_id, json.dumps(event))

                logger.debug(f"Timeline event added to {report_id}: {title}")

        except Exception as e:
            logger.error(f"Failed to add timeline event to {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to add timeline event",
                details=str(e),
                context={"report_id": report_id}
            )


# @retry_database_operation
async def add_comment(report_id: str, user_id: str, text: str) -> dict:
    """
    Add a comment to report (transaction: insert + increment counter).

    Args:
        report_id: Report UUID
        user_id: Username
        text: Comment text

    Returns:
        dict: Comment data with created_at
    """
    with ErrorContext("database", "add_comment"):
        try:
            async with get_db_connection() as conn:
                async with conn.transaction():
                    now = datetime.now(timezone.utc)

                    # Insert comment
                    row = await conn.fetchrow("""
                        INSERT INTO comments (report_id, text, author, created_at)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id, report_id, text, author, created_at
                    """, report_id, text, user_id, now)

                    # Increment comment count
                    await conn.execute("""
                        UPDATE reports
                        SET comment_count = comment_count + 1
                        WHERE id = $1
                    """, report_id)

                    comment = _row_to_dict(row)
                    logger.info(f"Comment added to report {report_id} by {user_id}")

                    return comment

        except Exception as e:
            logger.error(f"Failed to add comment to {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to add comment",
                details=str(e),
                context={"report_id": report_id}
            )


# @retry_database_operation
async def get_comments(
    report_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """
    Get comments for a report.

    Args:
        report_id: Report UUID
        limit: Maximum comments to return
        offset: Number of comments to skip

    Returns:
        List[dict]: List of comments
    """
    with ErrorContext("database", "get_comments"):
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch("""
                    SELECT id, report_id, text, author, created_at
                    FROM comments
                    WHERE report_id = $1
                    ORDER BY created_at ASC
                    LIMIT $2 OFFSET $3
                """, report_id, limit, offset)

                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get comments for {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve comments",
                details=str(e),
                context={"report_id": report_id}
            )


# @retry_database_operation
async def delete_comment(report_id: str, comment_id: str) -> bool:
    """
    Delete a comment (transaction: delete + decrement counter).

    Args:
        report_id: Report UUID
        comment_id: Comment UUID

    Returns:
        bool: True if deleted
    """
    with ErrorContext("database", "delete_comment"):
        try:
            async with get_db_connection() as conn:
                async with conn.transaction():
                    # Delete comment
                    result = await conn.execute("""
                        DELETE FROM comments
                        WHERE id = $1 AND report_id = $2
                    """, comment_id, report_id)

                    deleted = result.split()[-1] == '1'

                    if deleted:
                        # Decrement comment count
                        await conn.execute("""
                            UPDATE reports
                            SET comment_count = GREATEST(comment_count - 1, 0)
                            WHERE id = $1
                        """, report_id)

                        logger.info(f"Comment {comment_id} deleted from report {report_id}")

                    return deleted

        except Exception as e:
            logger.error(f"Failed to delete comment {comment_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to delete comment",
                details=str(e),
                context={"comment_id": comment_id}
            )


# @retry_database_operation
async def delete_report_by_id(report_id: str) -> bool:
    """
    Delete a report (CASCADE deletes comments automatically).

    Args:
        report_id: Report UUID

    Returns:
        bool: True if deleted
    """
    with ErrorContext("database", "delete_report"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    DELETE FROM reports WHERE id = $1
                """, report_id)

                deleted = result.split()[-1] == '1'

                if deleted:
                    logger.info(f"Report deleted: {report_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete report {report_id}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to delete report",
                details=str(e),
                context={"report_id": report_id}
            )


# @retry_database_operation
async def check_dhash_duplicates(dhash: str, threshold: int = 5) -> Optional[str]:
    """
    Check for duplicate reports using perceptual hash.

    Args:
        dhash: Image perceptual hash (dHash)
        threshold: Maximum Hamming distance for match

    Returns:
        str: ID of duplicate report or None
    """
    with ErrorContext("database", "check_dhash_duplicates"):
        try:
            from app.services.image_service import calculate_hamming_distance

            async with get_db_connection() as conn:
                # Query recent reports with same dhash_bucket (first 4 chars)
                dhash_bucket = dhash[:4]

                rows = await conn.fetch("""
                    SELECT id, image_hash
                    FROM reports
                    WHERE dhash_bucket = $1
                      AND status IN ('PENDING_VERIFICATION', 'VERIFIED')
                      AND created_at >= NOW() - INTERVAL '30 days'
                    LIMIT 20
                """, dhash_bucket)

                # Calculate Hamming distance for each candidate
                for row in rows:
                    if row['image_hash']:
                        distance = calculate_hamming_distance(dhash, row['image_hash'])
                        if distance <= threshold:
                            logger.info(f"Duplicate found: {row['id']} (distance: {distance})")
                            return str(row['id'])

                return None

        except Exception as e:
            logger.error(f"Failed to check duplicates: {e}", exc_info=True)
            # Graceful degradation - return None instead of raising
            return None


# @retry_database_operation
async def get_all_reports_raw() -> List[dict]:
    """
    Get all reports without pagination (admin use only).

    Returns:
        List[dict]: All reports
    """
    with ErrorContext("database", "get_all_reports_raw"):
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch("""
                    SELECT
                        id, title, description, category, severity,
                        latitude, longitude, geohash,
                        address, city, state, country,
                        status, image_urls, submitted_by,
                        upvote_count, comment_count,
                        created_at, updated_at
                    FROM reports
                    ORDER BY created_at DESC
                """)

                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get all reports: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve all reports",
                details=str(e)
            )


# @retry_database_operation
async def get_user_reports(username: str, limit: int = 50) -> List[dict]:
    """
    Get reports submitted by a user.

    Args:
        username: Username
        limit: Maximum reports to return

    Returns:
        List[dict]: User's reports
    """
    with ErrorContext("database", "get_user_reports"):
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch("""
                    SELECT
                        id, title, description, category, severity,
                        latitude, longitude, address, city,
                        status, image_urls,
                        upvote_count, comment_count,
                        created_at, updated_at
                    FROM reports
                    WHERE submitted_by = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, username, limit)

                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get reports for {username}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve user reports",
                details=str(e),
                context={"username": username}
            )


# ============================================================================
# USER FUNCTIONS (17 functions)
# ============================================================================

# @retry_database_operation
async def create_user(user_data: dict) -> Optional[str]:
    """
    Create a new user (atomic transaction with uniqueness checks).

    Args:
        user_data: User data dictionary

    Returns:
        str: Username on success, None if duplicate exists
    """
    with ErrorContext("database", "create_user"):
        try:
            async with get_db_connection() as conn:
                async with conn.transaction():
                    # Check username uniqueness
                    exists = await conn.fetchval(
                        "SELECT 1 FROM users WHERE username = $1",
                        user_data.get('username')
                    )
                    if exists:
                        logger.warning(f"Username already exists: {user_data.get('username')}")
                        return None

                    # Check email uniqueness (if provided)
                    if user_data.get('email'):
                        exists = await conn.fetchval(
                            "SELECT 1 FROM users WHERE email = $1",
                            user_data.get('email')
                        )
                        if exists:
                            logger.warning(f"Email already exists: {user_data.get('email')}")
                            return None

                    # Insert user
                    now = datetime.now(timezone.utc)

                    row = await conn.fetchrow("""
                        INSERT INTO users (
                            username, email, password_hash,
                            role, is_active, is_verified,
                            oauth_provider, oauth_id,
                            magic_link_token, magic_link_expires,
                            created_at, updated_at
                        ) VALUES (
                            $1, $2, $3,
                            $4, $5, $6,
                            $7, $8,
                            $9, $10,
                            $11, $11
                        ) RETURNING username
                    """,
                        user_data.get('username'),
                        user_data.get('email'),
                        user_data.get('password_hash'),
                        user_data.get('role', 'citizen'),
                        user_data.get('is_active', True),
                        user_data.get('is_verified', False),
                        user_data.get('oauth_provider'),
                        user_data.get('oauth_id'),
                        user_data.get('magic_link_token'),
                        user_data.get('magic_link_expires'),
                        now
                    )

                    username = row['username']
                    logger.info(f"User created: {username}")
                    return username

        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to create user",
                details=str(e),
                context={"username": user_data.get('username')}
            )


# @retry_database_operation
async def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username."""
    with ErrorContext("database", "get_user_by_username"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        username, email, password_hash,
                        role, is_active, is_verified,
                        oauth_provider, oauth_id,
                        created_at, updated_at,
                        city, state, country, lat, lng, location_address,
                        municipality_id
                    FROM users
                    WHERE username = $1
                """, username)

                return _row_to_dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get user {username}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve user",
                details=str(e),
                context={"username": username}
            )


# @retry_database_operation
async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    with ErrorContext("database", "get_user_by_email"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        username, email, password_hash,
                        role, is_active, is_verified,
                        oauth_provider, oauth_id,
                        created_at, updated_at,
                        city, state, country, lat, lng, location_address,
                        municipality_id
                    FROM users
                    WHERE email = $1
                """, email)

                return _row_to_dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get user by email: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve user by email",
                details=str(e)
            )


# @retry_database_operation
# @retry_database_operation
async def get_user_by_oauth(provider: str, oauth_id: str) -> Optional[dict]:
    """Get user by OAuth provider and ID."""
    with ErrorContext("database", "get_user_by_oauth"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        username, email, password_hash,
                        role, is_active, is_verified,
                        oauth_provider, oauth_id,
                        created_at, updated_at,
                        city, state, country, lat, lng, location_address
                    FROM users
                    WHERE oauth_provider = $1 AND oauth_id = $2
                """, provider, oauth_id)

                return _row_to_dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get user by OAuth: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve user by OAuth",
                details=str(e)
            )


# @retry_database_operation
async def get_user_by_id(user_id: str) -> Optional[dict]:
    """
    Get user by ID (username or email for legacy support).

    Args:
        user_id: Username or email

    Returns:
        dict: User data or None
    """
    # Try username first
    user = await get_user_by_username(user_id)
    if user:
        return user

    # Fallback to email
    return await get_user_by_email(user_id)


# @retry_database_operation
async def update_user(user_identifier: str, updates: dict) -> bool:
    """
    Update user fields.

    Args:
        user_identifier: Username or email
        updates: Dictionary of fields to update

    Returns:
        bool: True if updated
    """
    with ErrorContext("database", "update_user"):
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_count = 1

            for key, value in updates.items():
                if key in ['username', 'created_at']:
                    continue

                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

            # Always update updated_at
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.now(timezone.utc))
            param_count += 1

            # Add user_identifier as final parameter
            values.append(user_identifier)

            if not set_clauses:
                return False

            query = f"""
                UPDATE users
                SET {', '.join(set_clauses)}
                WHERE username = ${param_count} OR email = ${param_count}
            """

            async with get_db_connection() as conn:
                result = await conn.execute(query, *values)

                updated = result.split()[-1] == '1'
                if updated:
                    logger.info(f"User updated: {user_identifier}")

                return updated

        except Exception as e:
            logger.error(f"Failed to update user {user_identifier}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to update user",
                details=str(e),
                context={"user_id": user_identifier}
            )


async def update_user_by_email(email: str, updates: dict) -> bool:
    """
    Update user fields by email. This version allows updating username.
    Used during onboarding when user may not have a username yet.

    Args:
        email: User's email address
        updates: Dictionary of fields to update (can include 'username')

    Returns:
        bool: True if updated
    """
    with ErrorContext("database", "update_user_by_email"):
        try:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_count = 1

            for key, value in updates.items():
                # Only skip created_at, allow username to be set
                if key in ['created_at', 'email']:
                    continue

                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

            # Always update updated_at
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.now(timezone.utc))
            param_count += 1

            # Add email as final parameter
            values.append(email)

            if not set_clauses:
                return False

            query = f"""
                UPDATE users
                SET {', '.join(set_clauses)}
                WHERE email = ${param_count}
            """

            async with get_db_connection() as conn:
                result = await conn.execute(query, *values)

                updated = result.split()[-1] == '1'
                if updated:
                    logger.info(f"User updated by email: {email}")

                return updated

        except Exception as e:
            logger.error(f"Failed to update user by email {email}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to update user",
                details=str(e),
                context={"email": email}
            )

# @retry_database_operation
async def update_user_password(email: str, hashed_password: str) -> bool:
    """Update user password and clear reset token."""
    with ErrorContext("database", "update_user_password"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE users
                    SET
                        password_hash = $1,
                        password_reset_token = NULL,
                        password_reset_expires = NULL,
                        updated_at = $2
                    WHERE email = $3
                """, hashed_password, datetime.now(timezone.utc), email)

                updated = result.split()[-1] == '1'
                if updated:
                    logger.info(f"Password updated for user: {email}")

                return updated

        except Exception as e:
            logger.error(f"Failed to update password: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to update password",
                details=str(e)
            )


# @retry_database_operation
async def update_user_verification_token(
    email: str,
    token: str,
    token_type: str,
    expires_at: datetime
) -> bool:
    """
    Store verification token (email/phone/password_reset).

    Args:
        email: User email
        token: Verification token
        token_type: Type (email_verification, phone_verification, password_reset)
        expires_at: Token expiration

    Returns:
        bool: True if updated
    """
    with ErrorContext("database", "update_verification_token"):
        try:
            async with get_db_connection() as conn:
                # Determine which token field to update
                token_field = f"{token_type}_token"
                expires_field = f"{token_type}_expires"

                result = await conn.execute(f"""
                    UPDATE users
                    SET
                        {token_field} = $1,
                        {expires_field} = $2,
                        updated_at = $3
                    WHERE email = $4
                """, token, expires_at, datetime.now(timezone.utc), email)

                return result.split()[-1] == '1'

        except Exception as e:
            logger.error(f"Failed to update verification token: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to update verification token",
                details=str(e)
            )


# @retry_database_operation
async def get_user_by_verification_token(token: str, token_type: str) -> Optional[dict]:
    """
    Get user by verification token (if not expired).

    Args:
        token: Verification token
        token_type: Type (email_verification, phone_verification, password_reset)

    Returns:
        dict: User data or None
    """
    with ErrorContext("database", "get_user_by_verification_token"):
        try:
            token_field = f"{token_type}_token"
            expires_field = f"{token_type}_expires"

            async with get_db_connection() as conn:
                row = await conn.fetchrow(f"""
                    SELECT
                        username, email, password_hash,
                        role, is_active, is_verified,
                        created_at, updated_at,
                        city, state, country, lat, lng, location_address
                    FROM users
                    WHERE {token_field} = $1
                      AND {expires_field} > $2
                """, token, datetime.now(timezone.utc))

                return _row_to_dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get user by token: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to retrieve user by token",
                details=str(e)
            )


# @retry_database_operation
async def mark_email_verified(email: str) -> bool:
    """Mark user email as verified."""
    with ErrorContext("database", "mark_email_verified"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE users
                    SET
                        is_verified = true,
                        updated_at = $1
                    WHERE email = $2
                """, datetime.now(timezone.utc), email)

                verified = result.split()[-1] == '1'
                if verified:
                    logger.info(f"Email verified: {email}")

                return verified

        except Exception as e:
            logger.error(f"Failed to mark email verified: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to mark email verified",
                details=str(e)
            )


# @retry_database_operation
async def mark_phone_verified(phone: str) -> bool:
    """Mark user phone as verified."""
    with ErrorContext("database", "mark_phone_verified"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE users
                    SET
                        phone_verified = true,
                        phone_verification_code = NULL,
                        phone_verification_expires = NULL,
                        is_verified = true,
                        updated_at = $1
                    WHERE phone = $2
                """, datetime.now(timezone.utc), phone)

                verified = result.split()[-1] == '1'
                if verified:
                    logger.info(f"Phone verified: {phone}")

                return verified

        except Exception as e:
            logger.error(f"Failed to mark phone verified: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to mark phone verified",
                details=str(e)
            )


# @retry_database_operation
async def clear_verification_token(email: str, token_type: str) -> bool:
    """Clear verification token after use."""
    with ErrorContext("database", "clear_verification_token"):
        try:
            token_field = f"{token_type}_token"
            expires_field = f"{token_type}_expires"

            async with get_db_connection() as conn:
                result = await conn.execute(f"""
                    UPDATE users
                    SET
                        {token_field} = NULL,
                        {expires_field} = NULL,
                        updated_at = $1
                    WHERE email = $2
                """, datetime.now(timezone.utc), email)

                return result.split()[-1] == '1'

        except Exception as e:
            logger.error(f"Failed to clear verification token: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to clear verification token",
                details=str(e)
            )


# @retry_database_operation
async def get_user_stats_aggregated(username: str) -> dict:
    """
    Get user statistics with efficient SQL aggregation (single query).

    Args:
        username: Username to get stats for

    Returns:
        dict: Stats including total_reports, verified_reports, etc.
    """
    with ErrorContext("database", "get_user_stats_aggregated"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_reports,
                        COUNT(*) FILTER (WHERE status = 'VERIFIED') as verified_reports,
                        COUNT(*) FILTER (WHERE status = 'RESOLVED') as resolved_reports,
                        COUNT(*) FILTER (WHERE status = 'PENDING_VERIFICATION') as pending_reports,
                        COUNT(*) FILTER (WHERE status = 'IN_PROGRESS') as in_progress_reports,
                        COALESCE(SUM(upvote_count), 0) as total_upvotes
                    FROM reports
                    WHERE submitted_by = $1
                """, username)

                if row:
                    return {
                        "total_reports": row['total_reports'],
                        "verified_reports": row['verified_reports'],
                        "resolved_reports": row['resolved_reports'],
                        "pending_reports": row['pending_reports'],
                        "in_progress_reports": row['in_progress_reports'],
                        "total_upvotes": int(row['total_upvotes'])
                    }

                return {
                    "total_reports": 0,
                    "verified_reports": 0,
                    "resolved_reports": 0,
                    "pending_reports": 0,
                    "in_progress_reports": 0,
                    "total_upvotes": 0
                }

        except Exception as e:
            logger.error(f"Failed to get user stats: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to get user stats",
                details=str(e)
            )


# @retry_database_operation
async def get_user_by_email_lookup(email: str) -> Optional[dict]:
    """Alias for get_user_by_email (for compatibility)."""
    return await get_user_by_email(email)


# @retry_database_operation
async def delete_user(username: str) -> bool:
    """
    Delete user by username (CASCADE deletes all related records).

    Args:
        username: Username (primary key)

    Returns:
        bool: True if deleted
    """
    with ErrorContext("database", "delete_user"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    DELETE FROM users WHERE username = $1
                """, username)

                deleted = result.split()[-1] == '1'

                if deleted:
                    logger.info(f"User deleted: {username}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete user {username}: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to delete user",
                details=str(e),
                context={"username": username}
            )


# @retry_database_operation
async def get_user_by_magic_link_token(token: str) -> Optional[dict]:
    """
    Get user by magic link token (if not expired).
    
    Args:
        token: Magic link token
    
    Returns:
        dict: User data or None
    """
    with ErrorContext("database", "get_user_by_magic_link_token"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        username, email, phone, password_hash,
                        role, is_active, is_verified,
                        city, state, country, lat, lng, location_address,
                        oauth_provider, oauth_id,
                        magic_link_token, magic_link_expires,
                        created_at, updated_at
                    FROM users
                    WHERE magic_link_token = $1
                      AND (magic_link_expires IS NULL OR magic_link_expires > $2)
                """, token, datetime.now(timezone.utc))

                if not row:
                    logger.debug(f"No user found with magic link token")
                    return None

                user = dict(row)
                logger.debug(f"User found by magic link token: {user['username']}")
                return user

        except Exception as e:
            logger.error(f"Error getting user by magic link token: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to lookup user by magic link",
                details=str(e),
                context={"operation": "get_user_by_magic_link_token"}
            )


# ============================================================================
# USER METADATA FUNCTIONS (Admin-only visibility)
# ============================================================================

async def create_user_metadata(
    username: str,
    ip: str,
    city: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    isp: Optional[str] = None,
    timezone: Optional[str] = None,
    vpn_detected: bool = False
) -> Optional[str]:
    """
    Create user metadata record with signup location info.
    
    Args:
        username: Username (foreign key to users table)
        ip: Client IP address at signup
        city: City from IP geolocation
        region: Region/state from IP geolocation
        country: Country from IP geolocation
        country_code: ISO country code
        lat: Latitude from IP geolocation
        lng: Longitude from IP geolocation
        isp: Internet service provider
        timezone: Detected timezone
        vpn_detected: Whether VPN/proxy detected
    
    Returns:
        str: Metadata record ID on success, None on failure
    """
    with ErrorContext("database", "create_user_metadata"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO user_metadata (
                        username, signup_ip,
                        signup_city, signup_region, signup_country, signup_country_code,
                        signup_lat, signup_lng,
                        signup_isp, signup_timezone,
                        vpn_detected,
                        created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW()
                    )
                    ON CONFLICT (username) DO UPDATE SET
                        signup_ip = EXCLUDED.signup_ip,
                        signup_city = EXCLUDED.signup_city,
                        signup_region = EXCLUDED.signup_region,
                        signup_country = EXCLUDED.signup_country,
                        signup_country_code = EXCLUDED.signup_country_code,
                        signup_lat = EXCLUDED.signup_lat,
                        signup_lng = EXCLUDED.signup_lng,
                        signup_isp = EXCLUDED.signup_isp,
                        signup_timezone = EXCLUDED.signup_timezone,
                        vpn_detected = EXCLUDED.vpn_detected
                    RETURNING id
                """,
                    username, ip,
                    city, region, country, country_code,
                    lat, lng,
                    isp, timezone,
                    vpn_detected
                )
                
                if row:
                    logger.info(f"User metadata created for {username}: {city}, {country}")
                    return str(row['id'])
                return None
                
        except Exception as e:
            logger.error(f"Failed to create user metadata for {username}: {e}", exc_info=True)
            # Don't raise - metadata is non-critical
            return None


async def get_user_metadata(username: str) -> Optional[dict]:
    """
    Get user metadata by username (admin-only).
    
    Args:
        username: Username
    
    Returns:
        dict: User metadata or None
    """
    with ErrorContext("database", "get_user_metadata"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        id, username,
                        signup_ip, signup_city, signup_region, signup_country, signup_country_code,
                        signup_lat, signup_lng, signup_isp, signup_timezone,
                        location_mismatch, vpn_detected,
                        created_at
                    FROM user_metadata
                    WHERE username = $1
                """, username)
                
                return _row_to_dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Failed to get user metadata for {username}: {e}", exc_info=True)
            return None


async def update_location_mismatch(username: str, mismatch: bool) -> bool:
    """
    Update location_mismatch flag when user completes onboarding.
    
    Compares claimed city/country vs signup city/country.
    
    Args:
        username: Username
        mismatch: Whether there's a location mismatch
    
    Returns:
        bool: True if updated
    """
    with ErrorContext("database", "update_location_mismatch"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE user_metadata
                    SET location_mismatch = $2
                    WHERE username = $1
                """, username, mismatch)
                
                updated = result.split()[-1] == '1'
                if updated and mismatch:
                    logger.warning(f"Location mismatch detected for user {username}")
                return updated
                
        except Exception as e:
            logger.error(f"Failed to update location mismatch for {username}: {e}", exc_info=True)
            return False


async def check_location_mismatch(username: str, claimed_city: str, claimed_country: str = "India") -> bool:
    """
    Check if claimed location matches signup location.
    
    Args:
        username: Username
        claimed_city: City claimed by user during onboarding
        claimed_country: Country claimed by user
    
    Returns:
        bool: True if there's a mismatch (suspicious)
    """
    metadata = await get_user_metadata(username)
    if not metadata:
        return False  # No metadata = can't verify
    
    signup_city = metadata.get('signup_city', '')
    signup_country = metadata.get('signup_country', '')
    
    # Normalize for comparison
    claimed_city = (claimed_city or '').lower().strip()
    claimed_country = (claimed_country or '').lower().strip()
    signup_city = (signup_city or '').lower().strip()
    signup_country = (signup_country or '').lower().strip()
    
    # Country mismatch is very suspicious
    if signup_country and claimed_country and signup_country != claimed_country:
        logger.warning(f"Country mismatch for {username}: claimed={claimed_country}, signup={signup_country}")
        await update_location_mismatch(username, True)
        return True
    
    # City mismatch within same country is less suspicious but worth noting
    # People travel/move, so we don't flag this as strongly
    if signup_city and claimed_city and signup_city != claimed_city:
        # Only flag if countries also don't match or VPN detected
        if metadata.get('vpn_detected'):
            logger.warning(f"City mismatch with VPN for {username}: claimed={claimed_city}, signup={signup_city}")
            await update_location_mismatch(username, True)
            return True
    
    await update_location_mismatch(username, False)
    return False


async def get_users_with_metadata(limit: int = 50, mismatch_only: bool = False) -> List[dict]:
    """
    Get users with their metadata (admin dashboard use).
    
    Args:
        limit: Maximum users to return
        mismatch_only: If True, only return users with location mismatch
    
    Returns:
        List[dict]: Users with metadata joined
    """
    with ErrorContext("database", "get_users_with_metadata"):
        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT
                        u.username, u.email, u.city, u.state, u.country,
                        u.created_at as user_created_at,
                        m.signup_ip, m.signup_city, m.signup_region, m.signup_country,
                        m.location_mismatch, m.vpn_detected,
                        m.created_at as metadata_created_at
                    FROM users u
                    LEFT JOIN user_metadata m ON u.username = m.username
                """
                
                if mismatch_only:
                    query += " WHERE m.location_mismatch = true"
                
                query += " ORDER BY u.created_at DESC LIMIT $1"
                
                rows = await conn.fetch(query, limit)
                return _rows_to_list(rows)
                
        except Exception as e:
            logger.error(f"Failed to get users with metadata: {e}", exc_info=True)
            return []

# ============================================================================
# ALERT FUNCTIONS (Nagar Alert Hub)
# ============================================================================

async def create_alert(data: dict) -> str:
    """Create a new alert."""
    with ErrorContext("database", "create_alert"):
        try:
            async with get_db_connection() as conn:
                # Calculate expiration
                expires_in = data.get('expires_in_hours', 24)
                expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in)

                row = await conn.fetchrow("""
                    INSERT INTO alerts (
                        title, description, severity, category,
                        geohash, latitude, longitude, radius_meters,
                        status, source, author_id, expires_at
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7, $8,
                        $9, $10, $11, $12
                    ) RETURNING id
                """,
                    data['title'],
                    data.get('description'),
                    data.get('severity', 'medium'),
                    data.get('category'),
                    data.get('geohash'),
                    data.get('latitude'),
                    data.get('longitude'),
                    data.get('radius_meters', 0),
                    'ACTIVE',
                    data.get('source', 'authority'),
                    data.get('author_id'),
                    expires_at
                )
                return str(row['id'])
        except Exception as e:
            logger.error(f"Failed to create alert: {e}", exc_info=True)
            raise DatabaseError("Failed to create alert", details=str(e))

async def get_alerts(
    geohash: Optional[str] = None,
    district_code: Optional[int] = None,
    district_name: Optional[str] = None,
    state_name: Optional[str] = None,
    status: str = 'ACTIVE',
    limit: int = 50
) -> List[dict]:
    """
    Get alerts with flexible filtering:
    - district_code: Filter by LGD district code (preferred, most efficient)
    - district_name + state_name: Filter by text match (fallback)
    - geohash: Filter by geohash prefix (hyper-local)
    """
    with ErrorContext("database", "get_alerts"):
        try:
            async with get_db_connection() as conn:
                where_clauses = ["status = $1"]
                params: List[Any] = [status]
                param_count = 2

                if geohash:
                    where_clauses.append(f"geohash LIKE ${param_count}")
                    params.append(f"{geohash}%")
                    param_count += 1
                
                # District filtering - try code first, fall back to text
                if district_code:
                    # Check if district_code column exists
                    col_exists = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'broadcast_alerts' 
                            AND column_name = 'district_code'
                        )
                    """)
                    if col_exists:
                        where_clauses.append(f"district_code = ${param_count}")
                        params.append(district_code)
                        param_count += 1
                    else:
                        # Fallback: look up district name from districts table
                        district_info = await conn.fetchrow(
                            "SELECT district_name, state_name FROM districts WHERE district_code = $1",
                            district_code
                        )
                        if district_info:
                            where_clauses.append(f"LOWER(district) = LOWER(${param_count})")
                            params.append(district_info['district_name'])
                            param_count += 1
                            where_clauses.append(f"LOWER(state) = LOWER(${param_count})")
                            params.append(district_info['state_name'])
                            param_count += 1
                
                elif district_name:
                    where_clauses.append(f"LOWER(district) = LOWER(${param_count})")
                    params.append(district_name)
                    param_count += 1
                    if state_name:
                        where_clauses.append(f"LOWER(state) = LOWER(${param_count})")
                        params.append(state_name)
                        param_count += 1
                
                params.append(limit)

                query = f"""
                    SELECT * FROM broadcast_alerts
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY created_at DESC
                    LIMIT ${param_count}
                """
                
                rows = await conn.fetch(query, *params)
                return _rows_to_list(rows)
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}", exc_info=True)
            raise DatabaseError("Failed to fetch alerts", details=str(e))

# ============================================================================
# DASHBOARD ANALYTICS
# ============================================================================

async def get_dashboard_stats(municipality_id: str = None) -> dict:
    """
    Get high-level stats for the dashboard.
    TODO: implementations should filter by municipality_id once we have proper boundary mapping.
    For now, returns global stats or filtered by geohash if implemented.
    """
    with ErrorContext("database", "get_dashboard_stats"):
        try:
            async with get_db_connection() as conn:
                # 1. Counts
                counts = await conn.fetchrow("""
                    SELECT 
                        count(*) filter (where status = 'PENDING_VERIFICATION') as pending,
                        count(*) filter (where status = 'VERIFIED') as verified,
                        count(*) filter (where status = 'RESOLVED') as resolved,
                        count(*) as total
                    FROM reports
                """)
                
                # 2. Alerts count
                active_alerts = await conn.fetchval("SELECT count(*) FROM alerts WHERE status = 'ACTIVE'")
                
                # 3. Category distribution
                cat_rows = await conn.fetch("""
                    SELECT category, count(*) as c 
                    FROM reports 
                    GROUP BY category 
                    ORDER BY c DESC LIMIT 5
                """)
                categories = {r['category']: r['c'] for r in cat_rows}

                return {
                    "total_reports": counts['total'],
                    "pending_reports": counts['pending'],
                    "resolved_reports": counts['resolved'],
                    "avg_resolution_time_hours": 0, # TODO: Calculate this
                    "active_alerts": active_alerts,
                    "reports_by_category": categories,
                    "reports_by_status": {
                        "pending": counts['pending'],
                        "verified": counts['verified'],
                        "resolved": counts['resolved']
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}", exc_info=True)
            raise DatabaseError("Failed to get stats", details=str(e))


# ============================================================================
# ALERT CRUD FUNCTIONS (Extended for Nagar Alert Hub)
# ============================================================================

async def get_alert_by_id(alert_id: str) -> Optional[dict]:
    """Get alert by ID."""
    with ErrorContext("database", "get_alert_by_id"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM alerts WHERE id = $1
                """, alert_id)
                return _row_to_dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get alert {alert_id}: {e}", exc_info=True)
            raise DatabaseError("Failed to get alert", details=str(e))


async def update_alert(alert_id: str, updates: dict) -> bool:
    """
    Update alert fields.
    
    Args:
        alert_id: Alert UUID
        updates: Dictionary of fields to update
    
    Returns:
        bool: True if updated, False if not found
    """
    with ErrorContext("database", "update_alert"):
        try:
            set_clauses = []
            values = []
            param_count = 1

            for key, value in updates.items():
                if key in ['id', 'created_at']:
                    continue
                set_clauses.append(f"{key} = ${param_count}")
                values.append(value)
                param_count += 1

            # Always update updated_at
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.now(timezone.utc))
            param_count += 1

            values.append(alert_id)

            if not set_clauses:
                return False

            query = f"""
                UPDATE alerts
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """

            async with get_db_connection() as conn:
                result = await conn.execute(query, *values)
                updated = result.split()[-1] == '1'
                if updated:
                    logger.info(f"Alert updated: {alert_id}")
                return updated

        except Exception as e:
            logger.error(f"Failed to update alert {alert_id}: {e}", exc_info=True)
            raise DatabaseError("Failed to update alert", details=str(e))


async def end_alert(alert_id: str, resolved_by: str = None) -> bool:
    """
    End/resolve an active alert.
    
    Args:
        alert_id: Alert UUID
        resolved_by: Username of person ending the alert
    
    Returns:
        bool: True if ended
    """
    with ErrorContext("database", "end_alert"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE alerts
                    SET status = 'ENDED',
                        resolved_at = $2,
                        updated_at = $2
                    WHERE id = $1 AND status = 'ACTIVE'
                """, alert_id, datetime.now(timezone.utc))
                
                ended = result.split()[-1] == '1'
                if ended:
                    logger.info(f"Alert ended: {alert_id} by {resolved_by}")
                return ended

        except Exception as e:
            logger.error(f"Failed to end alert {alert_id}: {e}", exc_info=True)
            raise DatabaseError("Failed to end alert", details=str(e))


async def get_public_alerts(
    geohash: Optional[str] = None,
    categories: Optional[List[str]] = None,
    limit: int = 20
) -> List[dict]:
    """
    Get active alerts for public display.
    
    Args:
        geohash: Optional geohash prefix to filter by location
        categories: Optional list of categories to include
        limit: Maximum alerts to return
    
    Returns:
        List[dict]: Active alerts
    """
    with ErrorContext("database", "get_public_alerts"):
        try:
            async with get_db_connection() as conn:
                where_clauses = ["status = 'ACTIVE'", "(expires_at IS NULL OR expires_at > NOW())"]
                params = []
                param_count = 1

                if geohash:
                    where_clauses.append(f"(geohash LIKE ${param_count} OR radius_meters = 0)")
                    params.append(f"{geohash}%")
                    param_count += 1

                if categories:
                    where_clauses.append(f"category = ANY(${param_count})")
                    params.append(categories)
                    param_count += 1

                params.append(limit)

                query = f"""
                    SELECT 
                        id, title, description, severity, category,
                        geohash, latitude, longitude, radius_meters,
                        status, source, created_at, expires_at,
                        sent_count, delivery_count, read_count
                    FROM alerts
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY 
                        CASE severity 
                            WHEN 'critical' THEN 1 
                            WHEN 'high' THEN 2 
                            WHEN 'medium' THEN 3 
                            ELSE 4 
                        END,
                        created_at DESC
                    LIMIT ${param_count}
                """

                rows = await conn.fetch(query, *params)
                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get public alerts: {e}", exc_info=True)
            raise DatabaseError("Failed to get public alerts", details=str(e))


async def expire_old_alerts() -> int:
    """
    Mark expired alerts as EXPIRED. Should be called periodically.
    
    Returns:
        int: Number of alerts expired
    """
    with ErrorContext("database", "expire_old_alerts"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE alerts
                    SET status = 'EXPIRED', updated_at = NOW()
                    WHERE status = 'ACTIVE' 
                    AND expires_at IS NOT NULL 
                    AND expires_at < NOW()
                """)
                count = int(result.split()[-1])
                if count > 0:
                    logger.info(f"Expired {count} alerts")
                return count
        except Exception as e:
            logger.error(f"Failed to expire alerts: {e}", exc_info=True)
            return 0


# ============================================================================
# USER ALERT SUBSCRIPTION FUNCTIONS
# ============================================================================

async def get_user_alert_subscription(user_id: str) -> Optional[dict]:
    """Get user's alert subscription settings."""
    with ErrorContext("database", "get_user_alert_subscription"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM user_alert_subscriptions WHERE user_id = $1
                """, user_id)
                return _row_to_dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get subscription for {user_id}: {e}", exc_info=True)
            return None


async def upsert_user_alert_subscription(user_id: str, settings: dict) -> dict:
    """
    Create or update user alert subscription.
    
    Args:
        user_id: Username
        settings: Subscription settings dict
    
    Returns:
        dict: Updated subscription
    """
    with ErrorContext("database", "upsert_user_alert_subscription"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO user_alert_subscriptions (
                        user_id, home_geohash, work_geohash, custom_geohashes,
                        subscription_radius_km, categories, severity_threshold,
                        enabled, notify_in_app, notify_whatsapp, whatsapp_number,
                        quiet_hours_start, quiet_hours_end, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW()
                    )
                    ON CONFLICT (user_id) DO UPDATE SET
                        home_geohash = COALESCE($2, user_alert_subscriptions.home_geohash),
                        work_geohash = COALESCE($3, user_alert_subscriptions.work_geohash),
                        custom_geohashes = COALESCE($4, user_alert_subscriptions.custom_geohashes),
                        subscription_radius_km = COALESCE($5, user_alert_subscriptions.subscription_radius_km),
                        categories = COALESCE($6, user_alert_subscriptions.categories),
                        severity_threshold = COALESCE($7, user_alert_subscriptions.severity_threshold),
                        enabled = COALESCE($8, user_alert_subscriptions.enabled),
                        notify_in_app = COALESCE($9, user_alert_subscriptions.notify_in_app),
                        notify_whatsapp = COALESCE($10, user_alert_subscriptions.notify_whatsapp),
                        whatsapp_number = COALESCE($11, user_alert_subscriptions.whatsapp_number),
                        quiet_hours_start = $12,
                        quiet_hours_end = $13,
                        updated_at = NOW()
                    RETURNING *
                """,
                    user_id,
                    settings.get('home_geohash'),
                    settings.get('work_geohash'),
                    settings.get('custom_geohashes'),
                    settings.get('subscription_radius_km'),
                    settings.get('categories'),
                    settings.get('severity_threshold'),
                    settings.get('enabled'),
                    settings.get('notify_in_app'),
                    settings.get('notify_whatsapp'),
                    settings.get('whatsapp_number'),
                    settings.get('quiet_hours_start'),
                    settings.get('quiet_hours_end')
                )
                
                logger.info(f"Alert subscription upserted for {user_id}")
                return _row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to upsert subscription for {user_id}: {e}", exc_info=True)
            raise DatabaseError("Failed to update subscription", details=str(e))


async def get_users_for_alert(
    alert_geohash: str,
    alert_category: str,
    severity: str,
    limit: int = 1000
) -> List[dict]:
    """
    Get users who should receive an alert based on their subscriptions.
    
    Args:
        alert_geohash: Geohash of the alert location
        alert_category: Category of the alert
        severity: Severity level
        limit: Max users to return
    
    Returns:
        List[dict]: Users matching subscription criteria
    """
    with ErrorContext("database", "get_users_for_alert"):
        try:
            # Map severity to numeric order for comparison
            severity_order = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
            alert_severity_num = severity_order.get(severity.lower(), 2)
            
            async with get_db_connection() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        s.user_id, s.home_geohash, s.work_geohash,
                        s.notify_in_app, s.notify_whatsapp, s.whatsapp_number,
                        u.email
                    FROM user_alert_subscriptions s
                    JOIN users u ON s.user_id = u.username
                    WHERE s.enabled = true
                    AND $1 = ANY(s.categories)
                    AND (
                        s.home_geohash LIKE $2 
                        OR s.work_geohash LIKE $2
                        OR $2 LIKE ANY(s.custom_geohashes)
                    )
                    AND CASE s.severity_threshold
                        WHEN 'low' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'high' THEN 3
                        WHEN 'critical' THEN 4
                        ELSE 2
                    END <= $3
                    LIMIT $4
                """, 
                    alert_category,
                    f"{alert_geohash[:5]}%",  # Match geohash prefix (5 chars = ~5km)
                    alert_severity_num,
                    limit
                )
                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get users for alert: {e}", exc_info=True)
            return []


async def log_alert_delivery(
    alert_id: str,
    user_id: str,
    channel: str = 'in_app',
    status: str = 'sent'
) -> None:
    """Log that an alert was delivered to a user."""
    with ErrorContext("database", "log_alert_delivery"):
        try:
            async with get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO alert_delivery_log (alert_id, user_id, channel, status, sent_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT DO NOTHING
                """, alert_id, user_id, channel, status)
        except Exception as e:
            logger.error(f"Failed to log alert delivery: {e}", exc_info=True)


async def increment_alert_counts(alert_id: str, count_type: str = 'sent') -> None:
    """Increment alert delivery counters."""
    with ErrorContext("database", "increment_alert_counts"):
        try:
            column = {
                'sent': 'sent_count',
                'delivered': 'delivery_count',
                'read': 'read_count'
            }.get(count_type, 'sent_count')
            
            async with get_db_connection() as conn:
                await conn.execute(f"""
                    UPDATE alerts SET {column} = {column} + 1 WHERE id = $1
                """, alert_id)
        except Exception as e:
            logger.error(f"Failed to increment alert count: {e}", exc_info=True)


async def get_municipality_reports(
    geohash_prefix: Optional[str] = None,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """
    Get reports for municipality dashboard with filters.
    
    Args:
        geohash_prefix: Filter by area (optional)
        status_filter: Filter by status (optional)
        category_filter: Filter by category (optional)
        limit: Max reports to return
        offset: Pagination offset
    
    Returns:
        List[dict]: Reports matching criteria
    """
    with ErrorContext("database", "get_municipality_reports"):
        try:
            async with get_db_connection() as conn:
                where_clauses = []
                params = []
                param_count = 1

                if geohash_prefix:
                    where_clauses.append(f"geohash LIKE ${param_count}")
                    params.append(f"{geohash_prefix}%")
                    param_count += 1

                if status_filter:
                    where_clauses.append(f"status = ${param_count}")
                    params.append(status_filter)
                    param_count += 1

                if category_filter:
                    where_clauses.append(f"category = ${param_count}")
                    params.append(category_filter)
                    param_count += 1

                params.extend([limit, offset])

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"""
                    SELECT 
                        id, title, description, category, severity,
                        latitude, longitude, geohash, address, city,
                        status, image_urls, submitted_by, 
                        upvote_count, comment_count,
                        created_at, updated_at
                    FROM reports
                    {where_sql}
                    ORDER BY 
                        CASE status
                            WHEN 'PENDING_VERIFICATION' THEN 1
                            WHEN 'VERIFIED' THEN 2
                            ELSE 3
                        END,
                        created_at DESC
                    LIMIT ${param_count} OFFSET ${param_count + 1}
                """

                rows = await conn.fetch(query, *params)
                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get municipality reports: {e}", exc_info=True)
            raise DatabaseError("Failed to get reports", details=str(e))


# ============================================================================
# NOTIFICATION FUNCTIONS
# ============================================================================

async def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str = None,
    data: dict = None
) -> str:
    """Create an in-app notification for a user."""
    with ErrorContext("database", "create_notification"):
        try:
            async with get_db_connection() as conn:
                notification_id = await conn.fetchval("""
                    INSERT INTO notifications (user_id, type, title, message, data)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, user_id, notification_type, title, message, json.dumps(data or {}))
                return str(notification_id)
        except Exception as e:
            logger.error(f"Failed to create notification: {e}", exc_info=True)
            raise DatabaseError("Failed to create notification", details=str(e))


async def get_user_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50
) -> List[dict]:
    """Get notifications for a user."""
    with ErrorContext("database", "get_user_notifications"):
        try:
            async with get_db_connection() as conn:
                if unread_only:
                    query = """
                        SELECT id, type, title, message, data, read, read_at, created_at
                        FROM notifications
                        WHERE user_id = $1 AND read = FALSE
                        ORDER BY created_at DESC
                        LIMIT $2
                    """
                else:
                    query = """
                        SELECT id, type, title, message, data, read, read_at, created_at
                        FROM notifications
                        WHERE user_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                    """
                rows = await conn.fetch(query, user_id, limit)
                results = _rows_to_list(rows)
                for r in results:
                    if r.get('data'):
                        r['data'] = json.loads(r['data']) if isinstance(r['data'], str) else r['data']
                return results
        except Exception as e:
            logger.error(f"Failed to get notifications: {e}", exc_info=True)
            raise DatabaseError("Failed to get notifications", details=str(e))


async def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark a notification as read."""
    with ErrorContext("database", "mark_notification_read"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE notifications
                    SET read = TRUE, read_at = NOW()
                    WHERE id = $1 AND user_id = $2
                """, notification_id, user_id)
                return "UPDATE 1" in result
        except Exception as e:
            logger.error(f"Failed to mark notification read: {e}", exc_info=True)
            raise DatabaseError("Failed to mark notification read", details=str(e))


async def mark_all_notifications_read(user_id: str) -> int:
    """Mark all notifications as read for a user."""
    with ErrorContext("database", "mark_all_notifications_read"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE notifications
                    SET read = TRUE, read_at = NOW()
                    WHERE user_id = $1 AND read = FALSE
                """, user_id)
                count = int(result.split()[-1]) if result else 0
                return count
        except Exception as e:
            logger.error(f"Failed to mark all notifications read: {e}", exc_info=True)
            raise DatabaseError("Failed to mark all notifications read", details=str(e))


async def get_unread_notification_count(user_id: str) -> int:
    """Get count of unread notifications."""
    with ErrorContext("database", "get_unread_notification_count"):
        try:
            async with get_db_connection() as conn:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM notifications
                    WHERE user_id = $1 AND read = FALSE
                """, user_id)
                return count or 0
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}", exc_info=True)
            return 0


async def queue_notification(
    notification_type: str,
    recipient_id: str,
    title: str,
    body: str = None,
    data: dict = None
) -> str:
    """Queue a notification for async delivery."""
    with ErrorContext("database", "queue_notification"):
        try:
            async with get_db_connection() as conn:
                queue_id = await conn.fetchval("""
                    INSERT INTO notification_queue 
                    (notification_type, recipient_id, title, body, data)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, notification_type, recipient_id, title, body, json.dumps(data or {}))
                return str(queue_id)
        except Exception as e:
            logger.error(f"Failed to queue notification: {e}", exc_info=True)
            raise DatabaseError("Failed to queue notification", details=str(e))


async def get_pending_notifications(limit: int = 50) -> List[dict]:
    """Get pending notifications from queue for processing."""
    with ErrorContext("database", "get_pending_notifications"):
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch("""
                    SELECT id, notification_type, recipient_id, title, body, data, attempts
                    FROM notification_queue
                    WHERE status = 'pending' AND scheduled_at <= NOW() AND attempts < max_attempts
                    ORDER BY scheduled_at
                    LIMIT $1
                """, limit)
                return _rows_to_list(rows)
        except Exception as e:
            logger.error(f"Failed to get pending notifications: {e}", exc_info=True)
            return []


async def update_notification_queue_status(
    queue_id: str,
    status: str,
    error: str = None
) -> bool:
    """Update notification queue item status."""
    with ErrorContext("database", "update_notification_queue_status"):
        try:
            async with get_db_connection() as conn:
                if status == 'sent':
                    await conn.execute("""
                        UPDATE notification_queue
                        SET status = $2, sent_at = NOW(), attempts = attempts + 1
                        WHERE id = $1
                    """, queue_id, status)
                elif status == 'failed':
                    await conn.execute("""
                        UPDATE notification_queue
                        SET status = $2, error = $3, attempts = attempts + 1
                        WHERE id = $1
                    """, queue_id, status, error)
                else:
                    await conn.execute("""
                        UPDATE notification_queue
                        SET status = $2, attempts = attempts + 1
                        WHERE id = $1
                    """, queue_id, status)
                return True
        except Exception as e:
            logger.error(f"Failed to update queue status: {e}", exc_info=True)
            return False


# ============================================================================
# MUNICIPALITY FUNCTIONS
# ============================================================================

async def get_municipalities(include_inactive: bool = False) -> List[dict]:
    """Get all municipalities."""
    with ErrorContext("database", "get_municipalities"):
        try:
            async with get_db_connection() as conn:
                if include_inactive:
                    rows = await conn.fetch("""
                        SELECT id, name, short_code, state, jurisdiction_geohashes, is_active, created_at
                        FROM municipalities
                        ORDER BY name
                    """)
                else:
                    rows = await conn.fetch("""
                        SELECT id, name, short_code, state, jurisdiction_geohashes, is_active, created_at
                        FROM municipalities
                        WHERE is_active = TRUE
                        ORDER BY name
                    """)
                return _rows_to_list(rows)
        except Exception as e:
            logger.error(f"Failed to get municipalities: {e}", exc_info=True)
            return []


async def get_departments(municipality_id: str = None) -> List[dict]:
    """Get departments, optionally filtered by municipality."""
    with ErrorContext("database", "get_departments"):
        try:
            async with get_db_connection() as conn:
                if municipality_id:
                    rows = await conn.fetch("""
                        SELECT id, name, municipality_id, categories, is_active
                        FROM departments
                        WHERE (municipality_id = $1 OR municipality_id IS NULL) AND is_active = TRUE
                        ORDER BY name
                    """, municipality_id)
                else:
                    rows = await conn.fetch("""
                        SELECT id, name, municipality_id, categories, is_active
                        FROM departments
                        WHERE is_active = TRUE
                        ORDER BY name
                    """)
                return _rows_to_list(rows)
        except Exception as e:
            logger.error(f"Failed to get departments: {e}", exc_info=True)
            return []


async def assign_report_to_municipality(
    report_id: str,
    municipality_id: str,
    department_id: str = None,
    assigned_by: str = None,
    resolution_eta: datetime = None
) -> bool:
    """Assign a report to a municipality and optionally a department."""
    with ErrorContext("database", "assign_report_to_municipality"):
        try:
            async with get_db_connection() as conn:
                await conn.execute("""
                    UPDATE reports
                    SET assigned_municipality = $2,
                        assigned_department = $3,
                        assigned_by = $4,
                        assigned_at = NOW(),
                        resolution_eta = $5,
                        updated_at = NOW()
                    WHERE id = $1
                """, report_id, municipality_id, department_id, assigned_by, resolution_eta)
                return True
        except Exception as e:
            logger.error(f"Failed to assign report: {e}", exc_info=True)
            raise DatabaseError("Failed to assign report", details=str(e))


async def get_reports_by_municipality(
    municipality_id: str,
    status_filter: str = None,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """Get reports assigned to a municipality."""
    with ErrorContext("database", "get_reports_by_municipality"):
        try:
            async with get_db_connection() as conn:
                params = [municipality_id]
                where_clause = "assigned_municipality = $1"
                
                if status_filter:
                    where_clause += " AND status = $2"
                    params.append(status_filter)
                
                params.extend([limit, offset])
                
                query = f"""
                    SELECT 
                        id, title, description, category, severity,
                        latitude, longitude, geohash, address, city,
                        status, image_urls, submitted_by,
                        assigned_municipality, assigned_department, assigned_at, assigned_by,
                        resolution_eta, resolution_notes,
                        upvote_count, comment_count,
                        created_at, updated_at
                    FROM reports
                    WHERE {where_clause}
                    ORDER BY 
                        CASE status
                            WHEN 'PENDING_VERIFICATION' THEN 1
                            WHEN 'VERIFIED' THEN 2
                            WHEN 'IN_PROGRESS' THEN 3
                            ELSE 4
                        END,
                        created_at DESC
                    LIMIT ${len(params) - 1} OFFSET ${len(params)}
                """
                
                rows = await conn.fetch(query, *params)
                return _rows_to_list(rows)
        except Exception as e:
            logger.error(f"Failed to get municipality reports: {e}", exc_info=True)
            raise DatabaseError("Failed to get reports", details=str(e))


async def update_report_resolution(
    report_id: str,
    resolution_notes: str = None,
    resolution_eta: datetime = None
) -> bool:
    """Update resolution notes and ETA for a report."""
    with ErrorContext("database", "update_report_resolution"):
        try:
            async with get_db_connection() as conn:
                await conn.execute("""
                    UPDATE reports
                    SET resolution_notes = COALESCE($2, resolution_notes),
                        resolution_eta = COALESCE($3, resolution_eta),
                        updated_at = NOW()
                    WHERE id = $1
                """, report_id, resolution_notes, resolution_eta)
                return True
        except Exception as e:
            logger.error(f"Failed to update resolution: {e}", exc_info=True)
            raise DatabaseError("Failed to update resolution", details=str(e))


# ============================================================================
# AUDIT LOGS
# ============================================================================

async def create_audit_log(
    action_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    old_value: Optional[Dict] = None,
    new_value: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    ip_address: Optional[str] = None
) -> str:
    """Create a new audit log entry."""
    with ErrorContext("database", "create_audit_log"):
        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO audit_logs (
                    action_type, entity_type, entity_id, actor_id, actor_role,
                    old_value, new_value, metadata, ip_address
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, 
                action_type, entity_type, entity_id, actor_id, actor_role,
                json.dumps(old_value) if old_value else None,
                json.dumps(new_value) if new_value else None,
                json.dumps(metadata) if metadata else None,
                ip_address
            )
            return str(row['id'])

async def get_audit_logs_for_entity(
    entity_type: str,
    entity_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get audit logs for a specific entity."""
    with ErrorContext("database", "get_audit_logs_for_entity"):
        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM audit_logs
                WHERE entity_type = $1 AND entity_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            """, entity_type, entity_id, limit)
            
            return [_row_to_dict(row) for row in rows]

async def query_audit_logs(
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Query audit logs with filters."""
    with ErrorContext("database", "query_audit_logs"):
        async with get_db_connection() as conn:
            where_clauses = []
            params = []
            param_count = 1
            
            if action_type:
                where_clauses.append(f"action_type = ${param_count}")
                params.append(action_type)
                param_count += 1
                
            if entity_type:
                where_clauses.append(f"entity_type = ${param_count}")
                params.append(entity_type)
                param_count += 1
                
            if actor_id:
                where_clauses.append(f"actor_id = ${param_count}")
                params.append(actor_id)
                param_count += 1
                
            if from_date:
                where_clauses.append(f"created_at >= ${param_count}")
                params.append(from_date)
                param_count += 1
                
            if to_date:
                where_clauses.append(f"created_at <= ${param_count}")
                params.append(to_date)
                param_count += 1
                
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM audit_logs {where_sql}"
            total = await conn.fetchval(count_query, *params)
            
            # Get logs
            params.extend([limit, offset])
            query = f"""
                SELECT * FROM audit_logs
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            
            rows = await conn.fetch(query, *params)
            return {
                "logs": [_row_to_dict(row) for row in rows],
                "total": total
            }


# ============================================================================
# REPORT FLAGS
# ============================================================================

async def get_user_flag_for_report(user_id: str, report_id: str) -> Optional[Dict[str, Any]]:
    """Check if user has already flagged a report."""
    with ErrorContext("database", "get_user_flag_for_report"):
        async with get_db_connection() as conn:
            try:
                row = await conn.fetchrow("""
                    SELECT * FROM report_flags
                    WHERE user_id = $1 AND report_id = $2
                """, user_id, report_id)
                return _row_to_dict(row) if row else None
            except asyncpg.UndefinedTableError:
                # Table might not exist yet if migration hasn't run
                return None

async def create_report_flag(
    report_id: str,
    user_id: str,
    flag_type: str,
    reason: Optional[str] = None,
    image_url: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new report flag."""
    with ErrorContext("database", "create_report_flag"):
        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO report_flags (
                    report_id, user_id, flag_type, reason, image_url, status
                )
                VALUES ($1, $2, $3, $4, $5, 'pending')
                RETURNING *
            """, report_id, user_id, flag_type, reason, image_url)
            return _row_to_dict(row)

async def get_flag_rate_limits(user_id: str) -> Optional[Dict[str, Any]]:
    """Get rate limits for a user."""
    with ErrorContext("database", "get_flag_rate_limits"):
        async with get_db_connection() as conn:
            try:
                row = await conn.fetchrow("""
                    SELECT * FROM flag_rate_limits WHERE user_id = $1
                """, user_id)
                return _row_to_dict(row) if row else None
            except asyncpg.UndefinedTableError:
                return None

async def increment_flag_rate_limit(user_id: str) -> None:
    """Increment flag counters for a user."""
    with ErrorContext("database", "increment_flag_rate_limit"):
        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO flag_rate_limits (
                    user_id, hourly_count, daily_count, last_flag_at
                )
                VALUES ($1, 1, 1, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    hourly_count = flag_rate_limits.hourly_count + 1,
                    daily_count = flag_rate_limits.daily_count + 1,
                    last_flag_at = NOW()
            """)

async def reset_flag_hourly_limit(user_id: str) -> None:
    """Reset hourly flag limit."""
    with ErrorContext("database", "reset_flag_hourly_limit"):
        async with get_db_connection() as conn:
            await conn.execute("""
                UPDATE flag_rate_limits 
                SET hourly_count = 0, hourly_reset_at = NOW()
                WHERE user_id = $1
            """, user_id)

async def reset_flag_daily_limit(user_id: str) -> None:
    """Reset daily flag limit."""
    with ErrorContext("database", "reset_flag_daily_limit"):
        async with get_db_connection() as conn:
            await conn.execute("""
                UPDATE flag_rate_limits 
                SET daily_count = 0, daily_reset_at = CURRENT_DATE
                WHERE user_id = $1
            """, user_id)

async def get_pending_flags(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Get pending flags for admin review."""
    with ErrorContext("database", "get_pending_flags"):
        async with get_db_connection() as conn:
            # Get total count
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM report_flags WHERE status = 'pending'
            """)
            
            # Get flags with report details
            rows = await conn.fetch("""
                SELECT f.*, 
                       r.title as report_title, r.category as report_category,
                       officer.username as officer_username
                FROM report_flags f
                JOIN reports r ON f.report_id = r.id
                LEFT JOIN users officer ON r.assigned_by = officer.username
                WHERE f.status = 'pending'
                ORDER BY f.created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)
            
            return {
                "flags": [_row_to_dict(row) for row in rows],
                "total": total
            }

async def get_flag_by_id(flag_id: str) -> Optional[Dict[str, Any]]:
    """Get a flag by ID."""
    with ErrorContext("database", "get_flag_by_id"):
        async with get_db_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM report_flags WHERE id = $1", flag_id)
            return _row_to_dict(row) if row else None

async def update_flag_status(
    flag_id: str,
    status: str,
    reviewed_by: str,
    admin_note: Optional[str] = None
) -> Dict[str, Any]:
    """Update status of a flag."""
    with ErrorContext("database", "update_flag_status"):
        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                UPDATE report_flags
                SET status = $1, reviewed_by = $2, admin_note = $3, reviewed_at = NOW()
                WHERE id = $4
                RETURNING *
            """, status, reviewed_by, admin_note, flag_id)
            return _row_to_dict(row)

async def create_update_flag(
    update_id: str,
    user_id: str,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """Flag an individual update."""
    with ErrorContext("database", "create_update_flag"):
        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                INSERT INTO update_flags (update_id, user_id, reason, status)
                VALUES ($1, $2, $3, 'pending')
                RETURNING *
            """, update_id, user_id, reason)
            return _row_to_dict(row)

async def get_flag_stats() -> Dict[str, Any]:
    """Get statistics about flags."""
    with ErrorContext("database", "get_flag_stats"):
        async with get_db_connection() as conn:
            pending = await conn.fetchval(
                "SELECT COUNT(*) FROM report_flags WHERE status = 'pending'"
            )
            reviewed_today = await conn.fetchval("""
                SELECT COUNT(*) FROM report_flags 
                WHERE status != 'pending' 
                AND reviewed_at >= CURRENT_DATE::timestamp
            """)
            
            by_type = await conn.fetch("""
                SELECT flag_type, COUNT(*) as count 
                FROM report_flags 
                GROUP BY flag_type
            """)
            
            return {
                "pending_count": pending,
                "reviewed_today": reviewed_today,
                "by_type": {row['flag_type']: row['count'] for row in by_type}
            }


# ==========================================
# CITIES & MUNICIPALITIES
# ==========================================

async def get_cities(active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all cities."""
    with ErrorContext("database", "get_cities"):
        async with get_db_connection() as conn:
            query = "SELECT * FROM cities"
            if active_only:
                query += " WHERE is_active = true"
            query += " ORDER BY name ASC"
            
            rows = await conn.fetch(query)
            return [_row_to_dict(row) for row in rows]

async def get_city_by_id(city_id: str) -> Optional[Dict[str, Any]]:
    """Get city by ID."""
    with ErrorContext("database", "get_city_by_id"):
        async with get_db_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM cities WHERE id = $1", city_id)
            return _row_to_dict(row) if row else None

async def find_nearest_city_db(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Find the nearest city to a location using DB function."""
    with ErrorContext("database", "find_nearest_city"):
        async with get_db_connection() as conn:
            # We call the stored function if it exists, or replicate logic
            try:
                city_id = await conn.fetchval("SELECT find_nearest_city($1, $2)", lat, lng)
                if city_id:
                    return await get_city_by_id(str(city_id))
            except Exception:
                # Fallback implementation if function missing
                # Haversine distance calc in SQL
                row = await conn.fetchrow("""
                    SELECT *, (
                        6371 * acos(
                            cos(radians($1)) * cos(radians(latitude)) * cos(radians(longitude) - radians($2)) +
                            sin(radians($1)) * sin(radians(latitude))
                        )
                    ) as distance_km
                    FROM cities
                    WHERE is_active = true
                    ORDER BY distance_km ASC
                    LIMIT 1
                """, lat, lng)
                return _row_to_dict(row) if row else None
    return None


async def create_report_update(
    report_id: str,
    author_id: str,
    content: str,
    status: str = 'public',
    media_urls: Optional[List[str]] = None,
    is_official: bool = False
) -> dict:
    """
    Create a new update for a report.
    """
    with ErrorContext("database", "create_report_update"):
        try:
            async with get_db_connection() as conn:
                # Insert update
                row = await conn.fetchrow("""
                    INSERT INTO report_updates (
                        report_id, author_id, content, status, media_urls, is_official
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                """, report_id, author_id, content, status, media_urls or [], is_official)
                
                update = dict(row)
                
                # Log audit event
                await create_audit_log(
                    conn,
                    action_type="update_created",
                    entity_type="report_update",
                    entity_id=str(update['id']),
                    actor_id=author_id, 
                    metadata={
                        "report_id": report_id,
                        "is_official": is_official
                    }
                )
                
                return update

        except Exception as e:
            logger.error(f"Failed to create report update: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to create report update",
                details=str(e)
            )

async def get_report_updates(
    report_id: str,
    include_internal: bool = False
) -> List[dict]:
    """
    Get updates for a report.
    """
    with ErrorContext("database", "get_report_updates"):
        try:
            async with get_db_connection() as conn:
                where_clause = "report_id = $1"
                params = [report_id]
                
                if not include_internal:
                    where_clause += " AND status = 'public'"
                
                query = f"""
                    SELECT u.*, 
                           users.username as author_username,
                           users.role as author_role,
                           users.is_verified as author_is_verified
                    FROM report_updates u
                    LEFT JOIN users ON u.author_id = users.username
                    WHERE {where_clause}
                    ORDER BY u.created_at DESC
                """
                
                rows = await conn.fetch(query, *params)
                return _rows_to_list(rows)

        except Exception as e:
            logger.error(f"Failed to get report updates: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to get report updates",
                details=str(e)
            )




async def add_user_badge(username: str, badge: str) -> bool:
    """Add a badge to a user if they don't have it."""
    with ErrorContext("database", "add_user_badge"):
        try:
            async with get_db_connection() as conn:
                # Use array_append and distinct check
                result = await conn.execute("""
                    UPDATE users 
                    SET badges = array_append(badges, $2)
                    WHERE username = $1 AND NOT ($2 = ANY(badges))
                """, username, badge)
                return result.split()[-1] == '1'
        except Exception as e:
            logger.error(f"Failed to add badge {badge} to {username}: {e}")
            return False

async def update_user_reputation(username: str, points: int) -> int:
    """Update user reputation by adding points."""
    with ErrorContext("database", "update_user_reputation"):
        try:
            async with get_db_connection() as conn:
                new_score = await conn.fetchval("""
                    UPDATE users 
                    SET reputation = COALESCE(reputation, 0) + $2
                    WHERE username = $1
                    RETURNING reputation
                """, username, points)
                
                # Check for Local Guide badge (Example: > 100 points)
                if new_score and new_score >= 100:
                    await add_user_badge(username, "local_guide")
                    
                return new_score or 0
        except Exception as e:
            logger.error(f"Failed to update reputation for {username}: {e}")
            return 0

# ============================================================================
# MUNICIPALITY FUNCTIONS
# ============================================================================

async def get_municipalities(include_inactive: bool = False) -> List[dict]:
    """
    Get all municipalities.
    
    Args:
        include_inactive: If True, return inactive ones too
    
    Returns:
        List[dict]: List of municipalities
    """
    with ErrorContext("database", "get_municipalities"):
        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT
                        id, name, short_code, state, district,
                        latitude, longitude, radius_km,
                        population, website, is_active
                    FROM municipalities
                """
                
                if not include_inactive:
                    query += " WHERE is_active = true"
                    
                rows = await conn.fetch(query)
                return _rows_to_list(rows)
                
        except Exception as e:
            logger.error(f"Failed to get municipalities: {e}", exc_info=True)
            return []

async def get_municipality_by_id(muni_id: str) -> Optional[dict]:
    """Get municipality by ID."""
    with ErrorContext("database", "get_municipality_by_id"):
        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM municipalities WHERE id = $1
                """, muni_id)
                return _row_to_dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get municipality {muni_id}: {e}")
            return None

async def assign_report_to_municipality(
    report_id: str,
    municipality_id: str,
    department_id: Optional[str] = None,
    assigned_by: Optional[str] = None,
    resolution_eta: Optional[datetime] = None
) -> bool:
    """
    Assign a report to a municipality manually.
    """
    with ErrorContext("database", "assign_report_to_municipality"):
        try:
            async with get_db_connection() as conn:
                result = await conn.execute("""
                    UPDATE reports
                    SET 
                        assigned_municipality = $2,
                        assigned_department = $3,
                        assigned_by = $4,
                        resolution_eta = $5,
                        assigned_at = NOW(),
                        updated_at = NOW()
                    WHERE id = $1
                """, report_id, municipality_id, department_id, assigned_by, resolution_eta)
                
                return result.split()[-1] == '1'
        except Exception as e:
            logger.error(f"Failed to assign report: {e}")
            raise DatabaseError(message="Failed to assign report", details=str(e))

async def get_departments(municipality_id: Optional[str] = None) -> List[dict]:
    """Get departments."""
    with ErrorContext("database", "get_departments"):
        try:
            async with get_db_connection() as conn:
                query = "SELECT * FROM departments WHERE is_active = true"
                params = []
                if municipality_id:
                    query += " AND (municipality_id = $1 OR municipality_id IS NULL)"
                    params.append(municipality_id)
                
                rows = await conn.fetch(query, *params)
                return _rows_to_list(rows)
        except Exception as e:
            logger.error(f"Failed to get departments: {e}")
            return []

async def get_dashboard_stats(municipality_id: Optional[str] = None) -> dict:
    """
    Get dashboard stats, optionally filtered by municipality.
    """
    with ErrorContext("database", "get_dashboard_stats"):
        try:
            async with get_db_connection() as conn:
                filter_sql = ""
                params = []
                if municipality_id:
                    filter_sql = "WHERE assigned_municipality = $1"
                    params.append(municipality_id)
                
                # Simple count queries
                # Note: In production, these should be optimized or cached
                
                total = await conn.fetchval(f"SELECT count(*) FROM reports {filter_sql}", *params)
                
                pending_sql = f"WHERE status = 'PENDING_VERIFICATION'"
                if municipality_id: pending_sql += " AND assigned_municipality = $1"
                pending = await conn.fetchval(f"SELECT count(*) FROM reports {pending_sql}", *params)
                
                resolved_sql = f"WHERE status = 'RESOLVED'"
                if municipality_id: resolved_sql += " AND assigned_municipality = $1"
                resolved = await conn.fetchval(f"SELECT count(*) FROM reports {resolved_sql}", *params)
                
                return {
                    "total_reports": total,
                    "pending_reports": pending,
                    "resolved_reports": resolved,
                    "avg_resolution_time_hours": 0, # TODO: Calculate
                    "active_alerts": 0,
                    "reports_by_category": {},
                    "reports_by_status": {}
                }
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            raise

async def get_municipality_reports(
    geohash_prefix: Optional[str] = None,
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """Get reports for municipality dashboard."""
    # This function seems redundant with get_reports but specific for muni dashboard
    # TODO: Refactor to usage get_reports with municipality_id filter
    return []
