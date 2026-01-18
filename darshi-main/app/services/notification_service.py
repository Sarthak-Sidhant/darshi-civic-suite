"""
Notification Service

Handles creation, retrieval, and management of user notifications.
Supports in-app notifications and browser push notifications.
Uses PostgreSQL for notification storage.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.services import postgres_service as db_service
from app.models.notification import NotificationType
from app.core.logging_config import get_logger
from app.core.exceptions import DatabaseError, DocumentNotFoundError

logger = get_logger(__name__)


async def create_notification(
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    report_id: Optional[str] = None,
    comment_id: Optional[str] = None,
    actor: Optional[str] = None
) -> str:
    """
    Create a new notification for a user.

    Args:
        user_id: Username of the notification recipient
        notification_type: Type of notification
        title: Short notification title
        message: Notification message body
        report_id: Related report ID (optional)
        comment_id: Related comment ID (optional)
        actor: Who triggered the notification (optional)

    Returns:
        Created notification ID
    """
    try:
        data = {}
        if report_id:
            data['report_id'] = report_id
        if comment_id:
            data['comment_id'] = comment_id
        if actor:
            data['actor'] = actor

        notification_id = await db_service.create_notification(
            user_id=user_id,
            notification_type=notification_type.value if hasattr(notification_type, 'value') else str(notification_type),
            title=title,
            message=message,
            data=data
        )

        logger.info(f"Notification created for {user_id}: {title}")
        return notification_id

    except Exception as e:
        logger.error(f"Failed to create notification for {user_id}: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to create notification",
            details=str(e),
            context={"user_id": user_id, "type": str(notification_type)}
        ) from e


async def get_user_notifications(
    user_id: str,
    limit: int = 50,
    unread_only: bool = False
) -> List[Dict[str, Any]]:
    """Get notifications for a user."""
    try:
        notifications = await db_service.get_user_notifications(
            user_id=user_id,
            unread_only=unread_only,
            limit=limit
        )
        return notifications
    except Exception as e:
        logger.error(f"Failed to get notifications for {user_id}: {e}")
        return []


async def get_unread_count(user_id: str) -> int:
    """Get count of unread notifications for a user."""
    try:
        return await db_service.get_unread_notification_count(user_id)
    except Exception as e:
        logger.error(f"Failed to get unread count for {user_id}: {e}")
        return 0


async def mark_as_read(user_id: str, notification_id: str) -> bool:
    """Mark a notification as read."""
    try:
        return await db_service.mark_notification_read(notification_id, user_id)
    except Exception as e:
        logger.error(f"Failed to mark notification read: {e}")
        return False


async def mark_all_as_read(user_id: str) -> int:
    """Mark all notifications as read for a user."""
    try:
        return await db_service.mark_all_notifications_read(user_id)
    except Exception as e:
        logger.error(f"Failed to mark all notifications read: {e}")
        return 0


async def delete_notification(user_id: str, notification_id: str) -> bool:
    """Delete a notification."""
    # Note: Delete functionality not yet implemented in postgres_service
    # For now, just mark as read
    return await mark_as_read(user_id, notification_id)


# Browser Push Subscription Management

async def save_push_subscription(
    user_id: str,
    subscription_data: Dict[str, Any]
) -> str:
    """Save a browser push subscription for a user."""
    try:
        # Use existing push_subscriptions table
        from app.services import postgres_service as db
        async with db.get_db_connection() as conn:
            sub_id = await conn.fetchval("""
                INSERT INTO push_subscriptions (username, subscription)
                VALUES ($1, $2)
                ON CONFLICT (username) DO UPDATE SET subscription = $2
                RETURNING id
            """, user_id, subscription_data)
            return str(sub_id)
    except Exception as e:
        logger.error(f"Failed to save push subscription: {e}")
        return f"sub_{datetime.utcnow().timestamp()}"


async def remove_push_subscription(user_id: str, endpoint: str) -> bool:
    """Remove a push subscription by endpoint."""
    try:
        from app.services import postgres_service as db
        async with db.get_db_connection() as conn:
            await conn.execute("""
                DELETE FROM push_subscriptions
                WHERE username = $1 AND subscription->>'endpoint' = $2
            """, user_id, endpoint)
            return True
    except Exception as e:
        logger.error(f"Failed to remove push subscription: {e}")
        return False


async def send_browser_push(
    user_id: str,
    notification_id: str,
    title: str,
    message: str,
    report_id: Optional[str] = None
) -> bool:
    """
    Send browser push notification to all user's subscriptions.
    TODO: Implement actual push sending via web-push library.
    """
    try:
        # Queue the notification for async delivery
        data = {"notification_id": notification_id}
        if report_id:
            data["report_id"] = report_id

        await db_service.queue_notification(
            notification_type='push',
            recipient_id=user_id,
            title=title,
            body=message,
            data=data
        )
        return True
    except Exception as e:
        logger.error(f"Failed to queue push notification: {e}")
        return False


# Convenience function for sync contexts
def create_notification_sync(
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    **kwargs
) -> str:
    """Synchronous wrapper for create_notification."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule as task if already in async context
            asyncio.create_task(create_notification(user_id, notification_type, title, message, **kwargs))
            return f"notif_{datetime.utcnow().timestamp()}"
        else:
            return loop.run_until_complete(create_notification(user_id, notification_type, title, message, **kwargs))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(create_notification(user_id, notification_type, title, message, **kwargs))
