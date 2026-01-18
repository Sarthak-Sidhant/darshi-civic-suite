"""
Alert router - Public endpoints for viewing and interacting with alerts
City-based alerts using Nominatim for location detection
"""
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from typing import Optional, List
from datetime import datetime, timedelta
import geohash2

from app.core.alert_constants import ALERT_CATEGORIES, ALERT_SEVERITY, MAX_RADIUS_KM, DEFAULT_EXPIRY_HOURS, MAX_EXPIRY_HOURS
from app.services.postgres_service import get_db
from app.routers.auth import get_current_user, get_current_user_optional
from app.services.location_service import location_service
from app.services import storage_service
import uuid

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/in-district")
async def get_district_alerts(
    district: str = Query(..., description="District name"),
    state: str = Query(..., description="State name"),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    db = Depends(get_db)
):
    """Get active alerts in a specific district"""
    
    # Build query - use 'city' for backward compatibility until migration runs
    query = """
        SELECT 
            a.*,
            u.username as creator_username,
            m.name as municipality_name
        FROM broadcast_alerts a
        LEFT JOIN users u ON a.created_by = u.username
        LEFT JOIN municipalities m ON a.municipality_id = m.id
        WHERE a.status = 'ACTIVE'
          AND a.expires_at > NOW()
          AND LOWER(a.city) = LOWER($1)
          AND LOWER(a.state) = LOWER($2)
    """
    
    params = [district, state]
    
    if categories:
        query += " AND a.category = ANY($3)"
        params.append(categories.split(','))
    
    # Sort by: official first, then verified, then by upvotes + recency
    query += """
        ORDER BY 
            a.is_official DESC,
            (a.verified_by IS NOT NULL) DESC,
            a.upvote_count DESC,
            a.created_at DESC
        LIMIT 50
    """
    
    alerts = await db.fetch(query, *params)
    
    return [dict(alert) for alert in alerts]


@router.post("/create")
async def create_citizen_alert(
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    severity: str = Form(...),
    image: Optional[UploadFile] = File(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    radius_km: int = Form(5),
    expires_in_hours: int = Form(24),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create citizen alert with automatic city detection"""
    
    # Validate inputs
    if radius_km > MAX_RADIUS_KM:
        raise HTTPException(400, f"Radius cannot exceed {MAX_RADIUS_KM}km")
    
    if expires_in_hours > MAX_EXPIRY_HOURS:
        raise HTTPException(400, f"Expiry cannot exceed {MAX_EXPIRY_HOURS} hours")
    
    try:
        # 1. Reverse geocode to get district/state
        location_data = await location_service.reverse_geocode(latitude, longitude)
        if not location_data:
            raise HTTPException(400, "Could not determine district from location. Please try again.")
        
        district = location_data['district']
        district_code = location_data.get('district_code')
        state = location_data['state']
        address = location_data.get('address')
        
        # 2. Check if district has a municipality
        municipality = await location_service.get_municipality_for_district(district, state)
        municipality_id = municipality['id'] if municipality else None
        
        # 3. Upload image if provided
        image_urls = []
        if image:
            image_bytes = await image.read()
            image_url = storage_service.upload_file(image_bytes, image.content_type, image.filename)
            image_urls = [image_url]
            
        # 4. Calculate geohash
        
        # 4. Calculate geohash
        geohash = geohash2.encode(latitude, longitude, precision=6)
        
        # 5. Create alert
        alert_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        username = current_user['username']
        
        await db.execute("""
            INSERT INTO broadcast_alerts 
            (id, created_by, city, state, latitude, longitude, address,
             municipality_id, is_official, title, description, image_url, 
             category, severity, radius_km, geohash, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, FALSE, $9, $10, $11, $12, $13, $14, $15, $16)
        """, alert_id, username, district, state, latitude, longitude, address,
             municipality_id, title, description, image_urls[0] if image_urls else None, 
             category, severity, radius_km, geohash, expires_at)
        
        return {
            "id": alert_id,
            "status": "ACTIVE",
            "district": district,
            "state": state,
            "municipality_id": municipality_id,
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create alert: {str(e)}")



@router.get("/{alert_id}")
async def get_alert_details(
    alert_id: str,
    db = Depends(get_db)
):
    """Get full alert details"""
    
    alert = await db.fetchrow("""
        SELECT 
            a.*,
            u.username as creator_username,
            m.name as municipality_name,
            v.username as verifier_username
        FROM broadcast_alerts a
        LEFT JOIN users u ON a.created_by = u.username
        LEFT JOIN municipalities m ON a.municipality_id = m.id
        LEFT JOIN users v ON a.verified_by = v.username
        WHERE a.id = $1
    """, alert_id)
    
    if not alert:
        raise HTTPException(404, "Alert not found")
    
    # Increment view count
    await db.execute(
        "UPDATE broadcast_alerts SET view_count = view_count + 1 WHERE id = $1",
        alert_id
    )
    
    return dict(alert)


@router.post("/{alert_id}/upvote")
async def upvote_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Upvote a citizen alert"""
    
    username = current_user['username']
    
    # Check if alert exists and is citizen-created
    alert = await db.fetchrow(
        "SELECT is_official FROM broadcast_alerts WHERE id = $1",
        alert_id
    )
    
    if not alert:
        raise HTTPException(404, "Alert not found")
    
    if alert['is_official']:
        raise HTTPException(400, "Cannot upvote official municipality alerts")
    
    # Try to insert upvote
    try:
        await db.execute("""
            INSERT INTO alert_upvotes (alert_id, username)
            VALUES ($1, $2)
        """, alert_id, username)
        
        # Increment count
        result = await db.fetchrow("""
            UPDATE broadcast_alerts 
            SET upvote_count = upvote_count + 1
            WHERE id = $1
            RETURNING upvote_count
        """, alert_id)
        
        return {"status": "upvoted", "count": result['upvote_count']}
        
    except Exception:
        # Already upvoted - remove upvote
        await db.execute("""
            DELETE FROM alert_upvotes
            WHERE alert_id = $1 AND username = $2
        """, alert_id, username)
        
        result = await db.fetchrow("""
            UPDATE broadcast_alerts 
            SET upvote_count = upvote_count - 1
            WHERE id = $1
            RETURNING upvote_count
        """, alert_id)
        
        return {"status": "removed", "count": result['upvote_count']}


@router.post("/{alert_id}/comment")
async def add_alert_comment(
    alert_id: str,
    text: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Add comment to alert"""
    
    # Check if alert exists and is not expired
    alert = await db.fetchrow(
        "SELECT status FROM broadcast_alerts WHERE id = $1",
        alert_id
    )
    
    if not alert:
        raise HTTPException(404, "Alert not found")
    
    if alert['status'] == 'EXPIRED':
        raise HTTPException(400, "Cannot comment on expired alerts")
    
    # Create comment (reuse existing comments table)
    comment_id = generate_id("comment")
    username = current_user['username']
    
    await db.execute("""
        INSERT INTO comments (id, alert_id, username, text, created_at)
        VALUES ($1, $2, $3, $4, NOW())
    """, comment_id, alert_id, username, text)
    
    # Increment comment count
    await db.execute("""
        UPDATE broadcast_alerts 
        SET comment_count = comment_count + 1
        WHERE id = $1
    """, alert_id)
    
    return {
        "id": comment_id,
        "username": username,
        "text": text,
        "created_at": datetime.now().isoformat()
    }


@router.get("/{alert_id}/comments")
async def get_alert_comments(
    alert_id: str,
    db = Depends(get_db)
):
    """Get all comments for an alert"""
    
    comments = await db.fetch("""
        SELECT c.*, u.badges
        FROM comments c
        LEFT JOIN users u ON c.username = u.username
        WHERE c.alert_id = $1
        ORDER BY c.created_at DESC
    """, alert_id)
    
    return [dict(c) for c in comments]


@router.get("/{alert_id}/updates")
async def get_alert_updates(
    alert_id: str,
    db = Depends(get_db)
):
    """Get all updates for an alert"""
    
    updates = await db.fetch("""
        SELECT u.*, usr.role
        FROM alert_updates u
        LEFT JOIN users usr ON u.author_username = usr.username
        WHERE u.alert_id = $1
        ORDER BY u.created_at DESC
    """, alert_id)
    
    return [dict(u) for u in updates]
