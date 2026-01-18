"""
Notifications Router

REST API endpoints for managing user notifications.
"""

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from typing import Optional
from pydantic import BaseModel
from app.services import notification_service
from app.routers.auth import get_current_user
from app.core.security import limiter
from app.core.exceptions import DatabaseError, DocumentNotFoundError
from app.core.logging_config import get_logger

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
logger = get_logger(__name__)


class PushSubscribeRequest(BaseModel):
    """Request model for push subscription."""
    endpoint: str
    keys: dict  # {p256dh: str, auth: str}
    user_agent: Optional[str] = None


@router.get("")
@limiter.limit("30/minute")
async def get_notifications(
    request: Request,
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications"),
    current_user=Depends(get_current_user)
):
    """
    Get notifications for the current user.

    Returns notifications ordered by creation time (newest first).
    Includes unread count in the response.
    """
    try:
        notifications = await notification_service.get_user_notifications(
            user_id=current_user['username'],
            limit=limit,
            unread_only=unread_only
        )

        unread_count = await notification_service.get_unread_count(current_user['username'])

        logger.info(f"User {current_user['username']} fetched {len(notifications)} notifications")

        return {
            "notifications": notifications,
            "unread_count": unread_count
        }

    except DatabaseError as e:
        logger.error(f"Failed to fetch notifications for {current_user['username']}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{notification_id}/read")
@limiter.limit("100/minute")
async def mark_notification_read(
    request: Request,
    notification_id: str,
    current_user=Depends(get_current_user)
):
    """Mark a single notification as read."""
    try:
        success = await notification_service.mark_as_read(
            user_id=current_user['username'],
            notification_id=notification_id
        )

        logger.info(f"Notification {notification_id} marked as read by {current_user['username']}")

        return {"success": success}

    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/read-all")
@limiter.limit("20/minute")
async def mark_all_read(
    request: Request,
    current_user=Depends(get_current_user)
):
    """Mark all notifications as read for the current user."""
    try:
        count = await notification_service.mark_all_as_read(current_user['username'])

        logger.info(f"User {current_user['username']} marked {count} notifications as read")

        return {"marked_read": count}

    except DatabaseError as e:
        logger.error(f"Failed to mark all notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{notification_id}")
@limiter.limit("50/minute")
async def delete_notification(
    request: Request,
    notification_id: str,
    current_user=Depends(get_current_user)
):
    """Delete a notification."""
    try:
        success = await notification_service.delete_notification(
            user_id=current_user['username'],
            notification_id=notification_id
        )

        logger.info(f"Notification {notification_id} deleted by {current_user['username']}")

        return {"success": success}

    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(f"Failed to delete notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/push/subscribe")
@limiter.limit("10/minute")
async def subscribe_push(
    request: Request,
    subscription: PushSubscribeRequest,
    current_user=Depends(get_current_user)
):
    """Save browser push notification subscription."""
    try:
        subscription_id = await notification_service.save_push_subscription(
            user_id=current_user['username'],
            subscription_data=subscription.dict()
        )

        logger.info(f"Push subscription saved for user {current_user['username']}")

        return {
            "subscription_id": subscription_id,
            "message": "Push notifications enabled"
        }

    except DatabaseError as e:
        logger.error(f"Failed to save push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/push/unsubscribe")
@limiter.limit("10/minute")
async def unsubscribe_push(
    request: Request,
    endpoint: str = Query(..., description="Push subscription endpoint URL"),
    current_user=Depends(get_current_user)
):
    """Remove browser push notification subscription."""
    try:
        success = await notification_service.remove_push_subscription(
            user_id=current_user['username'],
            endpoint=endpoint
        )

        logger.info(f"Push subscription removed for user {current_user['username']}")

        return {
            "success": success,
            "message": "Push notifications disabled"
        }

    except DatabaseError as e:
        logger.error(f"Failed to remove push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
