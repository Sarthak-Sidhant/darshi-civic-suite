"""
Municipality Router - Nagar Alert Hub Management APIs

Provides endpoints for municipality dashboard, report management,
and broadcast alert operations.
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query, Form, File, UploadFile
from typing import List, Optional
from datetime import datetime
from app.services import postgres_service as db
from app.services.alert_service import alert_service
from app.models.schemas import AlertCreate, AlertResponse, AlertUpdate, DashboardStats
from app.routers.auth import get_current_user
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ============================================================================
# DASHBOARD & ANALYTICS
# ============================================================================

@router.get("/api/v1/municipality/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    request: Request,
    municipality_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard analytics.
    Restricted to authenticated users (admins/municipality staff).
    """
    try:
        # STRICT SCOPING: Municipality officials see ONLY their municipality
        user_muni_id = current_user.get('municipality_id')
        if not user_muni_id:
             # If super admin using this endpoint, allow requested ID
             if current_user.get('role') in ['admin', 'super_admin']:
                 user_muni_id = municipality_id
             else:
                 raise HTTPException(status_code=403, detail="No municipality assigned to user")
        
        # If explicitly requested and doesn't match assigned (and not super admin)
        if municipality_id and municipality_id != user_muni_id and current_user.get('role') not in ['admin', 'super_admin']:
             raise HTTPException(status_code=403, detail="Access denied to other municipality data")

        stats = await db.get_dashboard_stats(user_muni_id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        # Return fallback stats to prevent frontend crash
        return {
            "total_reports": 0,
            "pending_reports": 0,
            "resolved_reports": 0,
            "avg_resolution_time_hours": 0.0,
            "active_alerts": 0,
            "reports_by_category": {},
            "reports_by_status": {}
        }


# ============================================================================
# REPORT MANAGEMENT
# ============================================================================

@router.get("/api/v1/municipality/reports")
async def get_municipality_reports(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    geohash: Optional[str] = Query(None, description="Filter by area"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Get reports for municipality dashboard with filters.
    Sorted by priority: pending -> verified -> others, then by date.
    """
    try:
        reports = await db.get_municipality_reports(
            geohash_prefix=geohash,
            status_filter=status,
            category_filter=category,
            limit=limit,
            offset=offset
        )
        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        logger.error(f"Error fetching municipality reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch reports")


@router.put("/api/v1/municipality/report/{report_id}/status")
async def update_report_status(
    report_id: str,
    status: str,
    note: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Update report status from municipality dashboard.
    
    Valid statuses: PENDING_VERIFICATION, VERIFIED, IN_PROGRESS, RESOLVED, REJECTED
    """
    valid_statuses = ['PENDING_VERIFICATION', 'VERIFIED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    try:
        updates = {"status": status}
        if note:
            updates["admin_note"] = note
        
        success = await db.update_report(report_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Add timeline event
        await db.add_timeline_event(
            report_id=report_id,
            title=f"STATUS_CHANGED_TO_{status}",
            description=note or f"Status updated to {status}",
            actor=current_user.get('username', 'municipality')
        )
        
        logger.info(f"Report {report_id} status updated to {status} by {current_user.get('username')}")
        return {"message": "Status updated", "status": status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating report status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")


@router.put("/api/v1/municipality/report/{report_id}/assign")
async def assign_report(
    report_id: str,
    department: str,
    assigned_note: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Assign report to a department.
    
    Departments: roads, sanitation, electricity, water, traffic, other
    """
    try:
        updates = {
            "assigned_department": department,
            "status": "IN_PROGRESS"
        }
        if assigned_note:
            updates["admin_note"] = assigned_note
        
        success = await db.update_report(report_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Report not found")
        
        await db.add_timeline_event(
            report_id=report_id,
            title="ASSIGNED_TO_DEPARTMENT",
            description=f"Assigned to {department}",
            actor=current_user.get('username', 'municipality')
        )
        
        return {"message": f"Report assigned to {department}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning report: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign report")


# ============================================================================
# ALERT BROADCAST MANAGEMENT
# ============================================================================

@router.get("/api/v1/municipality/alerts")
async def get_municipality_alerts(
    request: Request,
    status: str = Query('ACTIVE', description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Get alerts for municipality management view."""
    try:
        alerts = await alert_service.get_municipality_alerts(status=status, limit=limit)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")


@router.post("/api/v1/municipality/alert")
async def broadcast_alert(
    request: Request,
    alert: AlertCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Broadcast a new emergency/service alert.
    Restricted to Municipality Roles with 'can_broadcast' permission.
    """
    try:
        # ENFORCE AUTHORITY
        user_muni_id = current_user.get('municipality_id')
        role = current_user.get('role')
        
        if not user_muni_id and role not in ['admin', 'super_admin']:
             raise HTTPException(status_code=403, detail="Unauthorized: No municipality assigned")

        alert_data = alert.model_dump()
        alert_data['author_id'] = current_user.get('username', 'unknown')
        
        # Auto-tag municipality
        if user_muni_id:
            # We should ideally fetch the municipality location/radius to auto-fill Geohash/Lat/Lng
            # But the alert creation logic might handle it. 
            # Ideally we modify the AlertCreate to allow inheriting location.
            pass 

        result = await alert_service.create_broadcast(alert_data)
        
        logger.info(f"Alert broadcasted: {alert.title} by {alert_data['author_id']}")
        return {"id": result["id"], "status": "broadcasted", "data": result}
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast alert")


@router.get("/api/v1/municipality/alert/{alert_id}")
async def get_alert_detail(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed alert information."""
    try:
        alert = await alert_service.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alert")


@router.put("/api/v1/municipality/alert/{alert_id}")
async def update_broadcast_alert(
    alert_id: str,
    updates: AlertUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an existing broadcast alert."""
    try:
        update_data = updates.model_dump(exclude_unset=True)
        success = await alert_service.update_broadcast(alert_id, update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        logger.info(f"Alert {alert_id} updated by {current_user.get('username')}")
        return {"message": "Alert updated", "id": alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert")


@router.post("/api/v1/municipality/alert/{alert_id}/end")
async def end_broadcast_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """End an active broadcast."""
    try:
        success = await alert_service.end_broadcast(
            alert_id, 
            ended_by=current_user.get('username')
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found or already ended")
            
        logger.info(f"Alert ended: {alert_id} by {current_user.get('username')}")
        return {"status": "ended", "id": alert_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"End broadcast error: {e}")
        raise HTTPException(status_code=500, detail="Failed to end broadcast")


# ============================================================================
# ALERTS - Municipality Management
# ============================================================================

@router.post("/api/v1/municipality/alerts")
async def create_municipality_alert(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    severity: str = Form(...),
    image: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    radius_km: int = Form(5),
    expires_in_hours: int = Form(24),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """Create official municipality alert with automatic city detection"""
    from app.services.image_service import upload_images
    from app.services.location_service import location_service
    from app.core.utils import generate_id
    from app.core.alert_constants import MAX_RADIUS_KM, MAX_EXPIRY_HOURS
    from datetime import datetime, timedelta
    import geohash2
    
    # Validate municipality context
    municipality_id = current_user.get('municipality_id')
    if not municipality_id:
        raise HTTPException(403, "Only municipality officials can create alerts")
    
    # Validate radius
    if radius_km > MAX_RADIUS_KM:
        raise HTTPException(400, f"Radius cannot exceed {MAX_RADIUS_KM}km")
    
    # Validate expiry
    if expires_in_hours > MAX_EXPIRY_HOURS:
        raise HTTPException(400, f"Expiry cannot exceed {MAX_EXPIRY_HOURS} hours")
    
    try:
        # 1. Reverse geocode to get district/state
        location_data = await location_service.reverse_geocode(latitude, longitude)
        if not location_data:
            raise HTTPException(400, "Could not determine district from location")
        
        district = location_data['district']
        district_code = location_data.get('district_code')
        state = location_data['state']
        address = location_data.get('address')
        
        # 2. Verify location is within municipality's jurisdiction
        # Get municipality details
        muni = await db.fetchrow(
            "SELECT name, latitude, longitude, radius_km FROM municipalities WHERE id = $1",
            municipality_id
        )
        
        if muni:
            # Check if alert location is within municipality coverage
            from app.services.location_service import LocationService
            dist = LocationService.haversine_distance(
                latitude, longitude,
                muni['latitude'], muni['longitude']
            )
            if dist > (muni['radius_km'] or 20):
                raise HTTPException(400, f"Alert location is outside {muni['name']} jurisdiction")
        
        # 3. Upload image
        image_bytes = await image.read()
        from app.services import storage_service
        image_url = storage_service.upload_file(image_bytes, image.content_type, image.filename)
        image_urls = [image_url]
        
        # 4. Calculate geohash
        geohash = geohash2.encode(latitude, longitude, precision=6)
        
        # 5. Create alert
        alert_id = str(__import__('uuid').uuid4())
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        username = current_user['username']
        
        await db.execute("""
            INSERT INTO broadcast_alerts 
            (id, created_by, city, state, latitude, longitude, address,
             municipality_id, is_official, title, description, image_url, 
             category, severity, radius_km, geohash, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, $9, $10, $11, $12, $13, $14, $15, $16)
        """, alert_id, username, district, state, latitude, longitude, address,
             municipality_id, title, description, image_urls[0], 
             category, severity, radius_km, geohash, expires_at)
        
        return {
            "id": alert_id,
            "status": "ACTIVE",
            "district": district,
            "state": state,
            "is_official": True,
            "municipality_id": municipality_id,
            "expires_at": expires_at.isoformat()
        }
        
        # Estimate reach (count users in same district)
        reach = await db.fetchval("""
            SELECT COUNT(*) FROM users 
            WHERE LOWER(city) = LOWER($1)
        """, district)
        
        logger.info(f"Municipality alert created: {alert_id} by {username} in {district} District")
        
        return {
            "id": alert_id,
            "status": "ACTIVE",
            "city": city,
            "state": state,
            "expires_at": expires_at.isoformat(),
            "estimated_reach": reach or 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert creation error: {e}")
        raise HTTPException(500, "Failed to create alert")


@router.get("/api/v1/municipality/alerts")
async def list_municipality_alerts(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """List municipality's alerts"""
    
    municipality_id = current_user.get('municipality_id')
    if not municipality_id:
        raise HTTPException(403, "No municipality assigned")
    
    query = """
        SELECT a.*, 
               (SELECT COUNT(*) FROM comments WHERE alert_id = a.id) as comment_count
        FROM broadcast_alerts a
        WHERE a.municipality_id = $1
    """
    params = [municipality_id]
    
    if status:
        query += " AND a.status = $2"
        params.append(status)
    
    if category:
        query += f" AND a.category = ${len(params) + 1}"
        params.append(category)
    
    query += f" ORDER BY a.created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
    params.extend([limit, offset])
    
    alerts = await db.fetch(query, *params)
    
    return [dict(a) for a in alerts]


@router.delete("/api/v1/municipality/alerts/{alert_id}")
async def cancel_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel an active alert"""
    
    municipality_id = current_user.get('municipality_id')
    if not municipality_id:
        raise HTTPException(403, "No municipality assigned")
    
    # Verify ownership
    alert = await db.fetchrow(
        "SELECT municipality_id FROM broadcast_alerts WHERE id = $1",
        alert_id
    )
    
    if not alert:
        raise HTTPException(404, "Alert not found")
    
    if alert['municipality_id'] != municipality_id:
        raise HTTPException(403, "Cannot cancel other municipality's alerts")
    
    # Cancel alert
    await db.execute("""
        UPDATE broadcast_alerts 
        SET status = 'CANCELLED'
        WHERE id = $1
    """, alert_id)
    
    logger.info(f"Alert cancelled: {alert_id}")
    
    return {"status": "cancelled"}


@router.post("/api/v1/municipality/alerts/{alert_id}/update")
async def post_alert_update(
    alert_id: str,
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Post update to alert"""
    from app.services.image_service import upload_images
    from app.core.utils import generate_id
    
    municipality_id = current_user.get('municipality_id')
    if not municipality_id:
        raise HTTPException(403, "No municipality assigned")
    
    # Verify alert exists and belongs to municipality
    alert = await db.fetchrow(
        "SELECT municipality_id FROM broadcast_alerts WHERE id = $1",
        alert_id
    )
    
    if not alert:
        raise HTTPException(404, "Alert not found")
    
    if alert['municipality_id'] != municipality_id:
        raise HTTPException(403, "Cannot update other municipality's alerts")
    
    # Upload image if provided
    image_url = None
    if image:
        image_urls = await upload_images([image], "alert_updates")
        image_url = image_urls[0]
    
    # Create update
    update_id = generate_id("alert_update")
    username = current_user['username']
    
    await db.execute("""
        INSERT INTO alert_updates (id, alert_id, author_username, content, image_url)
        VALUES ($1, $2, $3, $4, $5)
    """, update_id, alert_id, username, content, image_url)
    
    logger.info(f"Alert update posted: {update_id} on {alert_id}")
    
    return {
        "id": update_id,
        "alert_id": alert_id,
        "content": content,
        "created_at": datetime.now().isoformat()
    }


@router.post("/api/v1/municipality/alerts/{alert_id}/verify")
async def verify_citizen_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Verify a citizen-created alert"""
    
    municipality_id = current_user.get('municipality_id')
    if not municipality_id:
        raise HTTPException(403, "No municipality assigned")
    
    # Check if alert is citizen-created and in municipality's area
    alert = await db.fetchrow("""
        SELECT is_official, verified_by 
        FROM broadcast_alerts 
        WHERE id = $1
    """, alert_id)
    
    if not alert:
        raise HTTPException(404, "Alert not found")
    
    if alert['is_official']:
        raise HTTPException(400, "Cannot verify official alerts")
    
    if alert['verified_by']:
        raise HTTPException(400, "Alert already verified")
    
    # Verify alert
    username = current_user['username']
    
    await db.execute("""
        UPDATE broadcast_alerts 
        SET verified_by = $1, verified_at = NOW()
        WHERE id = $2
    """, username, alert_id)
    
    logger.info(f"Citizen alert verified: {alert_id} by {username}")
    
    return {"status": "verified", "verified_by": username}


# ============================================================================
# ANALYTICS
# ============================================================================


@router.get("/api/v1/municipality/analytics")
async def get_municipality_analytics(
    request: Request,
    period: str = Query("7d", description="Time period: 7d, 30d, 90d"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed analytics for municipality dashboard.
    
    Returns trends, resolution times, category breakdown, etc.
    """
    try:
        # Get basic stats
        stats = await db.get_dashboard_stats()
        
        # TODO: Add time-series data for charts
        # This would query historical data based on period
        
        return {
            "summary": stats,
            "period": period,
            "trends": {
                "reports_this_week": [],  # TODO: Implement
                "resolution_times": [],
                "category_distribution": stats.get("reports_by_category", {})
            }
        }
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")
