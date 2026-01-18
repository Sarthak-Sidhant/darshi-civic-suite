"""
User Alerts Router - Public Alert Endpoints

Provides public-facing alert APIs for citizens to view active alerts
and manage their alert subscription preferences.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.services import postgres_service as db
from app.services.alert_service import alert_service
from app.models.schemas import AlertSubscription, AlertSubscriptionResponse
from app.routers.auth import get_current_user
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# PUBLIC ALERT ENDPOINTS (No auth required)
# ============================================================================

@router.get("/api/v1/alerts")
async def get_public_alerts(
    geohash: Optional[str] = Query(None, description="Filter by location geohash"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get active public alerts.
    
    This is a public endpoint - no authentication required.
    Shows all active, non-expired alerts.
    """
    try:
        categories = [category] if category else None
        alerts = await alert_service.get_active_alerts(
            geohash=geohash,
            categories=categories,
            limit=limit
        )
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "filters": {
                "geohash": geohash,
                "category": category
            }
        }
    except Exception as e:
        logger.error(f"Error fetching public alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@router.get("/api/v1/alerts/{alert_id}")
async def get_alert_detail(alert_id: str):
    """
    Get details of a specific alert.
    
    Public endpoint - no authentication required.
    """
    try:
        alert = await alert_service.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert")


# ============================================================================
# USER ALERT PREFERENCES (Auth required)
# ============================================================================

@router.get("/api/v1/user/alert-preferences")
async def get_alert_preferences(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user's alert subscription preferences.
    
    Returns default settings if user hasn't configured preferences yet.
    """
    try:
        subscription = await alert_service.get_user_subscription(
            current_user['username']
        )
        
        if not subscription:
            # Return default preferences
            return {
                "user_id": current_user['username'],
                "enabled": True,
                "categories": ["traffic", "power", "water", "safety", "community"],
                "severity_threshold": "low",
                "notify_in_app": True,
                "notify_whatsapp": False,
                "subscription_radius_km": 5.0,
                "home_geohash": None,
                "work_geohash": None,
                "configured": False
            }
        
        subscription["configured"] = True
        return subscription
        
    except Exception as e:
        logger.error(f"Error fetching alert preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch preferences")


@router.put("/api/v1/user/alert-preferences")
async def update_alert_preferences(
    preferences: AlertSubscription,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user's alert subscription preferences.
    
    Allows users to:
    - Enable/disable alerts
    - Choose categories to receive
    - Set severity threshold
    - Configure location subscriptions
    - Set quiet hours
    """
    try:
        settings = preferences.model_dump(exclude_unset=True)
        
        result = await alert_service.update_user_subscription(
            user_id=current_user['username'],
            settings=settings
        )
        
        logger.info(f"Alert preferences updated for {current_user['username']}")
        return {
            "message": "Preferences updated",
            "subscription": result
        }
        
    except Exception as e:
        logger.error(f"Error updating alert preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")


@router.post("/api/v1/alerts/subscribe")
async def subscribe_to_alerts(
    preferences: AlertSubscription,
    current_user: dict = Depends(get_current_user)
):
    """
    Subscribe to receive alerts.
    
    Convenience endpoint that enables subscriptions with provided settings.
    """
    try:
        settings = preferences.model_dump()
        settings['enabled'] = True
        
        result = await alert_service.update_user_subscription(
            user_id=current_user['username'],
            settings=settings
        )
        
        logger.info(f"User {current_user['username']} subscribed to alerts")
        return {
            "message": "Successfully subscribed to alerts",
            "subscription": result
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe")


@router.post("/api/v1/alerts/unsubscribe")
async def unsubscribe_from_alerts(
    current_user: dict = Depends(get_current_user)
):
    """
    Unsubscribe from all alert notifications.
    
    Sets enabled=False but preserves other preferences.
    """
    try:
        result = await alert_service.update_user_subscription(
            user_id=current_user['username'],
            settings={'enabled': False}
        )
        
        logger.info(f"User {current_user['username']} unsubscribed from alerts")
        return {
            "message": "Successfully unsubscribed from alerts",
            "enabled": False
        }
        
    except Exception as e:
        logger.error(f"Error unsubscribing from alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")


@router.get("/api/v1/alerts/my-area")
async def get_alerts_in_my_area(
    current_user: dict = Depends(get_current_user)
):
    """
    Get alerts near the user's registered locations.
    
    Uses the user's home/work geohashes from their subscription
    or profile to filter alerts.
    """
    try:
        # First check for subscription with location
        subscription = await alert_service.get_user_subscription(
            current_user['username']
        )
        
        geohash = None
        if subscription:
            geohash = subscription.get('home_geohash') or subscription.get('work_geohash')
        
        # If no subscription, try to get from user profile
        if not geohash:
            user = await db.get_user_by_username(current_user['username'])
            if user and user.get('lat') and user.get('lng'):
                import pygeohash
                geohash = pygeohash.encode(user['lat'], user['lng'], precision=5)
        
        alerts = await alert_service.get_active_alerts(
            geohash=geohash,
            limit=20
        )
        
        return {
            "alerts": alerts,
            "count": len(alerts),
            "location_found": geohash is not None,
            "geohash_used": geohash[:3] if geohash else None  # Only show prefix for privacy
        }
        
    except Exception as e:
        logger.error(f"Error fetching alerts for user area: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@router.post("/api/v1/alerts/{alert_id}/mark-read")
async def mark_alert_read(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark an alert as read by the current user.
    
    Used for tracking engagement and analytics.
    """
    try:
        await db.increment_alert_counts(alert_id, 'read')
        
        # Update delivery log if exists
        # TODO: Update delivery log read_at timestamp
        
        return {"message": "Alert marked as read"}
        
    except Exception as e:
        logger.error(f"Error marking alert as read: {e}")
        # Don't fail the request for analytics errors
        return {"message": "Alert marked as read"}
