from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class NotificationType(str, Enum):
    """Types of notifications that can be sent to users."""
    REPORT_STATUS_CHANGE = "report_status_change"
    NEW_COMMENT = "new_comment"
    ADMIN_ACTION = "admin_action"
    UPVOTE_MILESTONE = "upvote_milestone"


class Notification(BaseModel):
    """
    Notification model for user notifications.

    Stored in Firestore as: users/{user_id}/notifications/{notification_id}
    """
    id: str
    user_id: str  # Recipient username
    type: NotificationType
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=500)
    read: bool = False
    created_at: datetime

    # Related entities
    report_id: Optional[str] = None
    comment_id: Optional[str] = None
    actor: Optional[str] = None  # Who triggered the notification (username or email)

    # Browser push tracking
    push_sent: bool = False
    push_sent_at: Optional[datetime] = None


class NotificationCreate(BaseModel):
    """Request model for creating notifications."""
    user_id: str
    type: NotificationType
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=500)
    report_id: Optional[str] = None
    comment_id: Optional[str] = None
    actor: Optional[str] = None


class PushSubscription(BaseModel):
    """Browser push notification subscription."""
    endpoint: str
    keys: dict  # Contains p256dh and auth keys
    user_agent: Optional[str] = None
    created_at: datetime
