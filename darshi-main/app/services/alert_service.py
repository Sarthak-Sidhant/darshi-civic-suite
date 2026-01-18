"""
Alert Service - Nagar Alert Hub

Database-backed alert service handling broadcast alerts, 
user subscriptions, and alert delivery coordination.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.core.logging_config import get_logger
from app.services import postgres_service as db

logger = get_logger(__name__)


class AlertService:
    """
    Service layer for Nagar Alert Hub functionality.
    
    Coordinates between database operations and provides
    higher-level alert management functions.
    """
    
    async def get_active_alerts(
        self, 
        geohash: Optional[str] = None,
        categories: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all active broadcast alerts.
        
        Args:
            geohash: Optional location filter
            categories: Optional category filter
            limit: Maximum alerts to return
        
        Returns:
            List of active alerts
        """
        try:
            alerts = await db.get_public_alerts(
                geohash=geohash,
                categories=categories,
                limit=limit
            )
            return alerts
        except Exception as e:
            logger.error(f"Error fetching active alerts: {e}")
            return []
    
    async def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert by ID."""
        try:
            return await db.get_alert_by_id(alert_id)
        except Exception as e:
            logger.error(f"Error fetching alert {alert_id}: {e}")
            return None

    async def create_broadcast(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create and broadcast a new alert.
        
        Args:
            data: Alert data including:
                - title (required)
                - description
                - category (required)
                - severity (low/medium/high/critical)
                - geohash / latitude / longitude
                - radius_meters
                - expires_in_hours
                - author_id
        
        Returns:
            Created alert data with ID
        """
        try:
            # Create alert in database
            alert_id = await db.create_alert(data)
            
            logger.info(f"Broadcast created: {data.get('title')} (ID: {alert_id})")
            
            # Get the created alert with full data
            alert = await db.get_alert_by_id(alert_id)
            
            # Trigger async notification job for subscribed users
            # This queues notifications for in-app delivery
            try:
                notified = await self._notify_subscribed_users(alert)
                logger.info(f"Alert {alert_id} delivered to {notified} subscribed users")
            except Exception as notify_err:
                # Don't fail alert creation if notifications fail
                logger.error(f"Notification delivery failed but alert created: {notify_err}")
            
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create broadcast: {e}")
            raise

    async def update_broadcast(self, alert_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing broadcast.
        
        Args:
            alert_id: Alert UUID
            updates: Fields to update
        
        Returns:
            True if updated successfully
        """
        try:
            return await db.update_alert(alert_id, updates)
        except Exception as e:
            logger.error(f"Failed to update broadcast {alert_id}: {e}")
            raise

    async def end_broadcast(self, alert_id: str, ended_by: str = None) -> bool:
        """
        End an active broadcast.
        
        Args:
            alert_id: Alert UUID
            ended_by: Username of person ending the alert
        
        Returns:
            True if ended successfully
        """
        try:
            return await db.end_alert(alert_id, ended_by)
        except Exception as e:
            logger.error(f"Failed to end broadcast {alert_id}: {e}")
            raise

    async def get_municipality_alerts(
        self,
        status: str = 'ACTIVE',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get alerts for municipality management view.
        
        Includes all statuses for management purposes.
        """
        try:
            return await db.get_alerts(status=status, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching municipality alerts: {e}")
            return []

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's alert subscription settings."""
        try:
            return await db.get_user_alert_subscription(user_id)
        except Exception as e:
            logger.error(f"Error fetching subscription for {user_id}: {e}")
            return None

    async def update_user_subscription(
        self, 
        user_id: str, 
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user's alert subscription settings.
        
        Args:
            user_id: Username
            settings: Subscription settings
        
        Returns:
            Updated subscription
        """
        try:
            return await db.upsert_user_alert_subscription(user_id, settings)
        except Exception as e:
            logger.error(f"Error updating subscription for {user_id}: {e}")
            raise

    async def expire_stale_alerts(self) -> int:
        """
        Mark expired alerts as EXPIRED.
        
        Should be called periodically (e.g., every 5 minutes).
        
        Returns:
            Number of alerts expired
        """
        try:
            return await db.expire_old_alerts()
        except Exception as e:
            logger.error(f"Error expiring alerts: {e}")
            return 0

    async def _notify_subscribed_users(self, alert: Dict[str, Any]) -> int:
        """
        Notify users who have subscribed to alerts in this area/category.
        
        This is a placeholder for the full notification pipeline.
        In production, this would:
        1. Query subscribed users
        2. Queue in-app notifications
        3. Queue WhatsApp messages (via worker)
        
        Returns:
            Number of users notified
        """
        try:
            if not alert.get('geohash') or not alert.get('category'):
                return 0
            
            users = await db.get_users_for_alert(
                alert_geohash=alert['geohash'],
                alert_category=alert['category'],
                severity=alert.get('severity', 'medium')
            )
            
            count = 0
            for user in users:
                # Log delivery attempt
                await db.log_alert_delivery(
                    alert_id=str(alert['id']),
                    user_id=user['user_id'],
                    channel='in_app',
                    status='sent'
                )
                count += 1
            
            # Update sent count
            if count > 0:
                await db.increment_alert_counts(str(alert['id']), 'sent')
            
            logger.info(f"Alert {alert['id']} sent to {count} users")
            return count
            
        except Exception as e:
            logger.error(f"Error notifying users for alert: {e}")
            return 0


# Export singleton instance
alert_service = AlertService()
