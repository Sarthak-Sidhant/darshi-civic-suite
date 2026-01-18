from typing import List, Optional
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks, Response, Request, Depends
from slowapi.util import get_remote_address
from app.services import ai_service, postgres_service as db_service, analytics_service, storage_service, geo_service, notification_service, image_service, location_service
from app.models.schemas import ReportResponse
from app.models.notification import NotificationType
from app.core.security import limiter, sanitize_form_data
from app.core.logging_config import get_logger
from app.routers.auth import get_current_user, get_current_user_optional
from pydantic import BaseModel
from app.core.validation import (
    validate_report_data,
    validate_file,
    validate_text_length
)
from app.core.exceptions import (
    DatabaseError,
    StorageError,
    AIServiceError
)
from app.core.error_handling import ErrorContext, safe_execute
import httpx

router = APIRouter()
logger = get_logger(__name__)

async def process_report_verification(report_id: str, image_url: str, user_lat: float, user_lng: float, report_context: dict = None):
    """
    Background Task:
    1. Download image
    2. Analyze with AI
    3. Check Duplicates
    4. Update DB Status
    5. Trigger External Integrations (if verified)
    """
    logger.info(f"Processing report {report_id} for verification")

    with ErrorContext("background_task", "verify_report", raise_on_exit=False):
        try:
            # 1. Download Image
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(image_url)
                if resp.status_code != 200:
                    logger.error(f"Failed to download image for report {report_id}: HTTP {resp.status_code}")
                    await db_service.update_report(report_id, {
                        "status": "FLAGGED",
                        "flag_reason": "Failed to download image for verification"
                    })
                    return
                image_bytes = resp.content

            # 2. Analyze with AI (with error handling)
            try:
                analysis = ai_service.analyze_image(image_bytes)
            except AIServiceError as e:
                logger.error(f"AI analysis failed for report {report_id}: {e}")
                await db_service.update_report(report_id, {
                    "status": "FLAGGED",
                    "flag_reason": f"AI analysis failed: {e.message}"
                })
                await db_service.add_timeline_event(report_id, "AI_ERROR", f"AI analysis error: {e.message}")
                return

            # Map integer severity (1-10) to string enum ('low', 'medium', 'high', 'critical')
            severity_score = analysis.severity
            severity_str = 'low'
            if severity_score >= 9:
                severity_str = 'critical'
            elif severity_score >= 7:
                severity_str = 'high'
            elif severity_score >= 5:
                severity_str = 'medium'

            # Store AI analysis as JSONB (the only AI-related column that exists)
            ai_analysis_data = {
                "is_valid": analysis.is_valid,
                "category": analysis.category,
                "severity": severity_score,
                "description": analysis.description
            }

            # Only use columns that actually exist in the reports table!
            updates = {
                "severity": severity_str,
                "ai_analysis": ai_analysis_data  # JSONB column
            }

            if not analysis.is_valid:
                updates["status"] = "REJECTED"
                rejection_reason = analysis.description or "AI could not identify a valid civic issue."
                updates["flag_reason"] = rejection_reason
            else:
                # AI verified the issue - mark as VERIFIED
                updates["status"] = "VERIFIED"
                updates["category"] = analysis.category

            # 4. Update DB FIRST (before timeline, so status is always updated)
            try:
                success = await db_service.update_report(report_id, updates)
                if success:
                    logger.info(f"Report {report_id} status updated to: {updates.get('status')}")
                else:
                    logger.error(f"Report {report_id} update returned False - report may not exist")
            except Exception as db_error:
                logger.error(f"CRITICAL: Failed to update report {report_id} status: {db_error}", exc_info=True)
                # Don't return - still try to add timeline for debugging
            
            try:
                if not analysis.is_valid:
                    await db_service.add_timeline_event(report_id, "AI_REJECTED", f"Rejected: {rejection_reason}")
                else:
                    await db_service.add_timeline_event(report_id, "VERIFIED", f"AI confirmed issue: {analysis.category}")
                    
                    # 5.1 Post to Reddit
                    try:
                        from app.services import reddit_service
                        # Add category to report context for title
                        if report_context:
                            report_context['category'] = analysis.category
                            
                        # Use image_url (R2 public URL)
                        reddit_service.post_report_to_reddit(report_data=report_context or {}, image_url=image_url)
                        logger.info(f"Report {report_id} posted to Reddit")
                    except Exception as reddit_error:
                        logger.warning(f"Failed to post to Reddit: {reddit_error}")

                    # 5.2 Trigger External Integrations (ONLY IF VERIFIED)
                    if report_context:
                        # Add AI data to context for Grivredr
                        report_context['ai_category'] = analysis.category # e.g. "pothole", "garbage"
                        
                        await process_external_integrations(
                            report_id=report_id,
                            report_data=report_context,
                            location_str=report_context.get('location', ''),
                            address_str=report_context.get('address', '')
                        )
                        
            except Exception as timeline_error:
                logger.warning(f"Failed to add timeline event for report {report_id}: {timeline_error}")

            # 6. Send notifications based on status
            try:
                report = await db_service.get_report_by_id(report_id)
                if report and report.get('submitted_by'):
                    status_val = updates.get('status')
                    report_title = report.get('title', 'Your report')
                    notification_title = ""
                    notification_message = ""

                    if status_val == "REJECTED":
                        notification_title = "Report Rejected"
                        notification_message = f"Your report '{report_title}' was rejected: {rejection_reason}"
                    elif status_val == "VERIFIED":
                        notification_title = "Report Verified ✓"
                        notification_message = f"Your report '{report_title}' has been verified!"
                    elif status_val == "DUPLICATE":
                        notification_title = "Duplicate Report"
                        notification_message = f"Your report '{report_title}' is a duplicate of an existing report."

                    if notification_title:
                        # Create in-app notification
                        notif_id = notification_service.create_notification(
                            user_id=report['submitted_by'],
                            notification_type=NotificationType.REPORT_STATUS_CHANGE,
                            title=notification_title,
                            message=notification_message,
                            report_id=report_id
                        )

                        # Send browser push notification (non-blocking)
                        try:
                            notification_service.send_browser_push(
                                user_id=report['submitted_by'],
                                notification_id=notif_id,
                                title=notification_title,
                                message=notification_message,
                                report_id=report_id
                            )
                        except Exception as push_error:
                            logger.warning(f"Browser push failed for report {report_id}: {push_error}")

            except Exception as e:
                # Don't fail the whole operation if notification fails
                logger.warning(f"Failed to send notification for report {report_id}: {e}")

        except httpx.TimeoutException as e:
            logger.error(f"Timeout downloading image for report {report_id}: {e}")
            try:
                await db_service.update_report(report_id, {
                    "status": "FLAGGED",
                    "flag_reason": "Image download timed out"
                })
            except Exception as flag_error:
                logger.error(f"Failed to flag report {report_id} after timeout: {flag_error}")

        except Exception as e:
            logger.error(f"Background verification failed for report {report_id}: {e}", exc_info=True)
            try:
                await db_service.update_report(report_id, {
                    "status": "FLAGGED",
                    "flag_reason": "System error during verification"
                })
            except Exception as flag_error:
                logger.error(f"Failed to flag report {report_id} after error: {flag_error}")

            try:
                await db_service.add_timeline_event(report_id, "SYSTEM_ERROR", "Verification failed.")
            except Exception as timeline_error:
                logger.error(f"Failed to add timeline event for report {report_id}: {timeline_error}")


async def process_report_geocoding(report_id: str, lat: float, lng: float):
    """
    Background Task: Reverse geocode coordinates and update report.
    Report is already created with coordinates - this enriches with address.
    """
    logger.info(f"Processing geocoding for report {report_id}")

    with ErrorContext("background_task", "geocode_report", raise_on_exit=False):
        try:
            address = await geo_service.reverse_geocode(lat, lng)

            if address and address != f"{lat}, {lng}":
                updates = {
                    "address": address
                }

                success = await db_service.update_report(report_id, updates)

                if success:
                    logger.info(f"Report {report_id} geocoded: {address}")
                    await db_service.add_timeline_event(
                        report_id,
                        "LOCATION_GEOCODED",
                        f"Address resolved: {address}"
                    )
                else:
                    logger.warning(f"Failed to update geocoded address for report {report_id}")
            else:
                logger.debug(f"Geocoding returned coordinates for report {report_id}")

        except Exception as e:
            logger.warning(f"Background geocoding failed for report {report_id}: {e}")


async def process_report_landmarks(report_id: str, lat: float, lng: float):
    """
    Background Task: Fetch nearby landmarks and update report.
    Report already created - this enriches with contextual location data.
    """
    logger.info(f"Processing landmarks for report {report_id}")

    with ErrorContext("background_task", "fetch_landmarks", raise_on_exit=False):
        try:
            landmarks = await geo_service.get_multiple_nearby_landmarks(
                lat=lat,
                lng=lng,
                radius_m=500,
                limit=5
            )

            if landmarks and len(landmarks) > 0:
                simplified_landmarks = [{
                    'name': lm['name'],
                    'type': lm['type'],
                    'distance_m': lm['distance_m']
                } for lm in landmarks]

                updates = {"landmarks": simplified_landmarks}
                success = await db_service.update_report(report_id, updates)

                if success:
                    logger.info(f"Report {report_id} enriched with {len(landmarks)} landmarks")
                    await db_service.add_timeline_event(
                        report_id,
                        "LANDMARKS_ADDED",
                        f"Found {len(landmarks)} nearby landmarks"
                    )
                else:
                    logger.warning(f"Failed to update landmarks for report {report_id}")
            else:
                logger.debug(f"No landmarks found near report {report_id}")

        except Exception as e:
            logger.warning(f"Background landmark lookup failed for report {report_id}: {e}")


async def process_external_integrations(report_id: str, report_data: dict, location_str: str, address_str: str):
    """
    Background Task: Check if report belongs to integrated municipalities (Ranchi) and trigger scraper.
    """
    is_ranchi = False
    
    # 1. Check strings (fast path)
    if "ranchi" in location_str.lower() or "ranchi" in address_str.lower():
        is_ranchi = True
    else:
        # 2. Check using Location Service (accurate path)
        try:
            # Parse lat/lng from location_str "lat,lng" if possible, or report_data
            lat = report_data.get('latitude')
            lng = report_data.get('longitude')
            
            if lat and lng:
                muni = await location_service.location_service.get_nearest_municipality(float(lat), float(lng))
                if muni and "ranchi" in muni['name'].lower():
                    is_ranchi = True
                    logger.info(f"Report {report_id} matched to Ranchi via Location Service")
        except Exception as e:
            logger.warning(f"Location service check failed during integration trigger: {e}")

    if is_ranchi:
        logger.info(f"Report {report_id} identified as Ranchi. Triggering external integration.")
        
        try:
            # Map AI Category to Ranchi Portal Problem ID
            ai_category = report_data.get('ai_category', '').lower()
            problem_type = '491' # Default: Dumping of cow dung/Garbage
            
            # Simple mapping logic (expand as needed based on portal IDs)
            if 'pothole' in ai_category or 'road' in ai_category:
                problem_type = '491' # Fallback as specific ID unknown, user mentioned 'filling form' logic
            elif 'water' in ai_category:
                problem_type = '484' # Barrier in water supply
            elif 'garbage' in ai_category or 'waste' in ai_category:
                problem_type = '491'
            elif 'light' in ai_category or 'electricity' in ai_category:
                problem_type = '-1' # Other (Manual)
            
            # Prepare payload for Grivredr
            payload = {
                "report_id": report_id,
                "name": report_data.get("username") or "Citizen",
                "description": report_data.get("description") or report_data.get("title"),
                "address": address_str or location_str,
                "latitude": report_data.get("latitude"),
                "longitude": report_data.get("longitude"),
                "problem_type": problem_type,
                "ai_category": ai_category
            }
            
            # Use grivredr service name from docker-compose
            grivredr_url = "http://grivredr:8000/submit"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(grivredr_url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Triggered Grivredr for report {report_id}")
                    await db_service.add_timeline_event(report_id, "EXTERNAL_PROCESSING", "Report forwarded to Ranchi Smart City Portal processing queue.")
                else:
                    logger.error(f"Failed to trigger Grivredr: {resp.status_code} - {resp.text}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger external integration for report {report_id}: {e}")



async def apply_dynamic_rate_limit(request: Request, is_authenticated: bool):
    """
    Apply different rate limits based on authentication status.
    Anonymous: 10/hour, Authenticated: 50/hour (5x more)

    Uses Redis for distributed rate limiting across multiple workers.
    Falls back to in-memory if Redis is unavailable.
    """
    from app.core.config import settings
    
    # Skip rate limiting if disabled
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    from slowapi.util import get_ipaddr
    from app.core.redis_client import get_redis_client
    import time
    import hashlib

    # Determine rate limit and key
    if is_authenticated:
        limit = 50  # 50 reports per hour for authenticated
        auth_header = request.headers.get("Authorization", "")
        # Use SHA-256 hash of token as key for authenticated users
        key = f"rate:auth:{hashlib.sha256(auth_header.encode()).hexdigest()}"
    else:
        limit = 10  # 10 reports per hour for anonymous (5x less)
        # Use IP address for anonymous users
        key = f"rate:anon:{get_ipaddr(request)}"

    redis_client = get_redis_client()

    if redis_client:
        # Use Redis sliding window rate limiting
        try:
            current_time = int(time.time())
            window_start = current_time - 3600  # 1 hour window

            # Use Redis sorted set for sliding window
            pipe = redis_client.pipeline()
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries in window
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            # Set expiry on the key (auto-cleanup)
            pipe.expire(key, 3600)
            results = pipe.execute()

            current_count = results[1]

            if current_count >= limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. {'Authenticated' if is_authenticated else 'Anonymous'} users can submit {limit} reports per hour. Please try again later."
                )
            return
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, falling back to in-memory: {e}")

    # Fallback to in-memory rate limiting (for single worker or Redis unavailable)
    if not hasattr(apply_dynamic_rate_limit, "rate_limits"):
        apply_dynamic_rate_limit.rate_limits = {}

    current_time = time.time()
    hour_ago = current_time - 3600

    if key not in apply_dynamic_rate_limit.rate_limits:
        apply_dynamic_rate_limit.rate_limits[key] = []

    # Clean old entries
    apply_dynamic_rate_limit.rate_limits[key] = [
        timestamp for timestamp in apply_dynamic_rate_limit.rate_limits[key]
        if timestamp > hour_ago
    ]

    if len(apply_dynamic_rate_limit.rate_limits[key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. {'Authenticated' if is_authenticated else 'Anonymous'} users can submit {limit} reports per hour. Please try again later."
        )

    apply_dynamic_rate_limit.rate_limits[key].append(current_time)

@router.post("/api/v1/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    location: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
):
    """
    Create a new report with comprehensive validation and error handling.
    Anonymous users: 10 reports/hour.
    Authenticated users: 50 reports/hour (5x more).
    """
    # 0. Check authentication and get user
    from app.routers.auth import get_current_user_optional

    authenticated_user = await get_current_user_optional(request)

    # Apply dynamic rate limit based on authentication
    await apply_dynamic_rate_limit(request, authenticated_user is not None)

    # Determine username: authenticated user takes precedence
    # For anonymous users, we use None (NULL in database) since submitted_by has FK constraint
    final_username = None
    if authenticated_user:
        final_username = authenticated_user.get('username')
    elif username:
        # Verify the provided username exists in database
        existing_user = await db_service.get_user_by_username(username)
        if existing_user:
            final_username = username
        # If username doesn't exist, leave as None (anonymous)

    is_anonymous = final_username is None
    display_username = final_username or "anonymous"
    logger.info(f"Report submission by {display_username} (authenticated: {authenticated_user is not None}, anonymous: {is_anonymous})")

    # 1. Validate files
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one image file is required")

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images allowed per report")

    # 2. Sanitize inputs
    sanitized = sanitize_form_data({
        "title": title,
        "description": description,
        "username": final_username,
        "location": location
    })

    # 3. Validate report data (includes coordinate validation)
    try:
        lat, lng = validate_report_data(
            title=sanitized["title"],
            location=sanitized["location"],
            description=sanitized["description"],
            username=final_username
        )
    except Exception as e:
        logger.warning(f"Report validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # 4. Validate and process first file
    first_file = files[0]

    try:
        content = await first_file.read()

        # Validate file
        validate_file(content, first_file.content_type, first_file.filename)

    except Exception as e:
        logger.warning(f"File validation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid file: {str(e)}")

    # 5. Process Image: Optimize (WebP + JPEG) and Calculate dHash
    try:
        processed = image_service.process_report_image(content)
        dhash = processed['dhash']
        webp_bytes = processed['webp_bytes']
        jpeg_bytes = processed['jpeg_bytes']

        logger.info(f"Image processed successfully, dHash: {dhash}")
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")

    # 6. Duplicate Check (dHash - perceptual hashing, survives crops/edits)
    try:
        existing_id = await db_service.check_dhash_duplicates(dhash, threshold=5)
        if existing_id:
            logger.info(f"Visually similar image detected, linking to report {existing_id}")
            return ReportResponse(report_id=existing_id, status="DUPLICATE_LINKED")
    except DatabaseError as e:
        logger.warning(f"dHash check failed: {e}. Continuing with report creation.")

    # 7. Upload Images to GCS (WebP + JPEG for browser compatibility)
    image_data = []

    async def upload_optimized_image(webp: bytes, jpeg: bytes) -> Optional[dict]:
        """Upload optimized image pair and return URLs or None on failure."""
        try:
            loop = asyncio.get_event_loop()
            urls = await loop.run_in_executor(
                None,
                storage_service.upload_optimized_image,
                webp,
                jpeg
            )
            return urls
        except Exception as e:
            logger.warning(f"Failed to upload optimized image: {e}")
            return None

    try:
        # Process and upload first image
        images_to_upload = [(webp_bytes, jpeg_bytes)]

        # Process remaining images
        for i in range(1, len(files)):
            f = files[i]
            try:
                c = await f.read()
                validate_file(c, f.content_type, f.filename)

                # Process image
                processed = image_service.process_report_image(c)
                images_to_upload.append((processed['webp_bytes'], processed['jpeg_bytes']))

            except Exception as e:
                logger.warning(f"Failed to process file {i+1}: {e}")

        # Upload all images in parallel
        upload_tasks = [
            upload_optimized_image(webp, jpeg)
            for webp, jpeg in images_to_upload
        ]
        results = await asyncio.gather(*upload_tasks)

        # Collect successful uploads (each result has webp_url and jpeg_url)
        image_data = [urls for urls in results if urls is not None]

        if not image_data:
            raise StorageError(message="All file uploads failed")

    except StorageError as e:
        logger.error(f"Storage error during upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload images: {e.message}"
        )

    # 7. Save Initial Report with sanitized data

    # Store coordinates initially - geocode in background
    human_location = f"{lat}, {lng}"
    logger.debug(f"Report will be created with coordinates (geocoding in background)")

    report_data = {
        "username": sanitized["username"],
        "title": sanitized["title"],
        "description": sanitized["description"],
        "location": human_location,  # Human-readable address
        "address": human_location,  # Same as location for now
        "latitude": lat,  # Store coordinates separately for map display
        "longitude": lng,
        "image_urls": [img['webp_url'] for img in image_data],  # Extract WebP URLs for database
        "image_hash": dhash,  # Perceptual dHash for duplicate detection
        "dhash_bucket": dhash[:4] if dhash and len(dhash) >= 4 else "",  # Bucket for O(1) duplicate lookup
        "submitted_by": sanitized["username"],  # Add submitted_by field
        "status": "PENDING_VERIFICATION",
        "category": "Uncategorized",
        "severity": "medium",  # Default severity as string
        "upvote_count": 0,
        "upvotes": []  # Fixed: was "upvoters", should be "upvotes"
    }

    # GEOHASHING
    try:
        gh = geo_service.encode(lat, lng)
        report_data['geohash'] = gh
    except Exception as e:
        logger.warning(f"Geohash encoding failed: {e}. Report will be created without geohash.")

    # KEYWORDS (Poor Man's Search)
    try:
        search_text = (sanitized["title"] + " " + (sanitized["description"] or "")).lower()
        report_data['keywords'] = list(set(search_text.split()))[-10:]
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")

    # Landmarks will be fetched in background task after report creation

    # Create report in database
    try:
        report_id = await db_service.create_report(report_data)
        logger.info(f"Report {report_id} created successfully by {final_username}")
    except DatabaseError as e:
        logger.error(f"Failed to create report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create report: {e.message}"
        )

    # 8. Trigger Background Tasks
    if image_data:
        # AI verification (now includes Trigger for External Integrations if verified)
        first_image_url = image_data[0]['webp_url']
        
        # Prepare context for verification task
        report_context = {
            "username": final_username,
            "title": sanitized["title"],
            "description": sanitized["description"],
            "location": sanitized["location"],
            "address": human_location,
            "latitude": lat,
            "longitude": lng
        }
        
        background_tasks.add_task(process_report_verification, report_id, first_image_url, lat, lng, report_context)

        # Reverse geocoding (parallel with AI verification)
        background_tasks.add_task(process_report_geocoding, report_id, lat, lng)

        # Landmark lookup (parallel with AI verification)
        background_tasks.add_task(process_report_landmarks, report_id, lat, lng)

    return ReportResponse(report_id=report_id, status="PENDING_VERIFICATION")

@router.post("/api/v1/report/{report_id}/upvote")
@limiter.limit("100/hour")
async def upvote_report(
    request: Request,
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Upvote a report. User must be authenticated.
    SECURITY: Username is extracted from JWT token to prevent IDOR attacks.
    """
    username = current_user.get('username') or current_user.get('email')
    if not username:
        raise HTTPException(status_code=500, detail="User identity not found in token")

    result = await db_service.upvote_report(report_id, username)
    if result.get("error") is not None:
        raise HTTPException(status_code=400, detail=result["error"])

    # Send notification for upvote milestones
    try:
        new_count = result.get('count', 0)  # Fixed: db service returns 'count', not 'upvote_count'
        milestones = [10, 50, 100, 500, 1000]

        if new_count in milestones:
            report = await db_service.get_report_by_id(report_id)
            if report and report.get('username'):
                report_title = report.get('title', 'Your report')
                notification_title = f"{new_count} Upvotes! 🎉"
                notification_message = f"Your report '{report_title}' reached {new_count} upvotes!"

                # Create in-app notification
                notif_id = notification_service.create_notification(
                    user_id=report['username'],
                    notification_type=NotificationType.UPVOTE_MILESTONE,
                    title=notification_title,
                    message=notification_message,
                    report_id=report_id
                )

                # Send browser push notification (non-blocking)
                try:
                    notification_service.send_browser_push(
                        user_id=report['username'],
                        notification_id=notif_id,
                        title=notification_title,
                        message=notification_message,
                        report_id=report_id
                    )
                except Exception as push_error:
                    logger.warning(f"Browser push failed for upvote milestone on report {report_id}: {push_error}")

    except Exception as e:
        # Don't fail the whole operation if notification fails
        logger.warning(f"Failed to send upvote milestone notification for report {report_id}: {e}")

    return result


@router.get("/api/v1/report/{report_id}")
@limiter.limit("200/hour")
async def get_report(request: Request, report_id: str, response: Response = None):
    from app.routers.auth import get_current_user_optional

    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Get optional current user for has_upvoted field
    current_user = await get_current_user_optional(request)
    current_user_id = current_user.get('username') if current_user else None

    # Add has_upvoted field based on current user
    upvotes = report.get('upvotes', [])
    report['has_upvoted'] = current_user_id in upvotes if current_user_id else False
    # Remove upvotes array from response (no need to expose who upvoted)
    report.pop('upvotes', None)

    # Cache individual reports for 1 minute (only for unauthenticated users)
    if response and not current_user:
        response.headers["Cache-Control"] = "public, max-age=60, s-maxage=120"
    return report

@router.post("/api/v1/report/{report_id}/comment")
@limiter.limit("50/hour")
async def add_comment(
    request: Request,
    report_id: str,
    text: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a comment to a report. User must be authenticated.
    SECURITY: Username is extracted from JWT token to prevent IDOR attacks.
    """
    username = current_user.get('username') or current_user.get('email')
    if not username:
        raise HTTPException(status_code=500, detail="User identity not found in token")

    # Validate comment length (max 500 characters)
    validate_text_length(text, "Comment", min_length=1, max_length=500)

    # Sanitize comment text
    sanitized = sanitize_form_data({"text": text})

    comment = await db_service.add_comment(report_id, username, sanitized["text"])
    if not comment:
        raise HTTPException(status_code=500, detail="Failed to add comment")

    # Send notification to report author (don't notify self)
    try:
        report = await db_service.get_report_by_id(report_id)
        if report and report.get('username') and report['username'] != username:
            report_title = report.get('title', 'Your report')
            notification_title = "New Comment"
            notification_message = f"{username} commented on your report '{report_title}'"

            # Create in-app notification
            notif_id = notification_service.create_notification(
                user_id=report['username'],
                notification_type=NotificationType.NEW_COMMENT,
                title=notification_title,
                message=notification_message,
                report_id=report_id,
                comment_id=comment.get('id'),
                actor=username
            )

            # Send browser push notification (non-blocking)
            try:
                notification_service.send_browser_push(
                    user_id=report['username'],
                    notification_id=notif_id,
                    title=notification_title,
                    message=notification_message,
                    report_id=report_id
                )
            except Exception as push_error:
                logger.warning(f"Browser push failed for comment on report {report_id}: {push_error}")

    except Exception as e:
        # Don't fail the whole operation if notification fails
        logger.warning(f"Failed to send comment notification for report {report_id}: {e}")

    return comment

@router.get("/api/v1/report/{report_id}/comments")
@limiter.limit("200/hour")
async def get_comments(request: Request, report_id: str):
    return await db_service.get_comments(report_id)

@router.get("/api/v1/reports")
@limiter.limit("200/hour")
async def get_reports(
    request: Request, 
    start_after_id: Optional[str] = None, 
    geohash: Optional[str] = None, 
    district_code: Optional[int] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 10, 
    response: Response = None
):
    from app.routers.auth import get_current_user_optional

    # Get optional current user for has_upvoted field
    current_user = await get_current_user_optional(request)
    current_user_id = current_user.get('username') if current_user else None

    reports = await db_service.get_reports(
        start_after_id=start_after_id, 
        geohash=geohash, 
        district_code=district_code,
        district_name=district,
        state_name=state,
        limit=limit, 
        current_user_id=current_user_id
    )
    # Add cache headers for better performance (only for unauthenticated users)
    if response and not current_user:
        response.headers["Cache-Control"] = "public, max-age=30, s-maxage=60"
    return reports

@router.get("/api/v1/geocode")
@limiter.limit("100/hour")
async def geocode(request: Request, q: str):
    return await geo_service.geocode_address(q)

@router.get("/api/v1/reverse-geocode")
@limiter.limit("100/hour")
async def reverse_geocode_endpoint(request: Request, lat: float, lng: float):
    """Get human-readable address from coordinates."""
    address = await geo_service.reverse_geocode(lat, lng)
    return {"address": address}

@router.get("/api/v1/reverse-geocode-detailed")
@limiter.limit("100/hour")
async def reverse_geocode_detailed_endpoint(request: Request, lat: float, lng: float):
    """
    Get detailed structured address from coordinates.
    Used for onboarding location detection.
    Returns city, state, country, and full address.
    """
    from app.core.http_client import get_http_client
    
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1,
        }
        headers = {"User-Agent": "Darshi-Civic-App/1.0"}
        
        client = get_http_client()
        resp = await client.get(url, params=params, headers=headers, timeout=30.0)
        
        if resp.status_code == 200:
            data = resp.json()
            address_parts = data.get('address', {})
            
            # Extract structured address components
            city = (address_parts.get('city') or
                   address_parts.get('town') or
                   address_parts.get('village') or
                   address_parts.get('municipality') or
                   address_parts.get('county') or
                   '')
            
            state = (address_parts.get('state') or
                    address_parts.get('state_district') or
                    '')
            
            country = address_parts.get('country', 'India')
            
            return {
                "display_name": data.get('display_name', f"{lat}, {lng}"),
                "address": {
                    "city": city,
                    "state": state,
                    "country": country,
                    "postcode": address_parts.get('postcode', ''),
                    "road": address_parts.get('road', ''),
                    "suburb": address_parts.get('suburb') or address_parts.get('neighbourhood', ''),
                }
            }
        
        return {"display_name": f"{lat}, {lng}", "address": {}}
        
    except Exception as e:
        logger.warning(f"Detailed reverse geocode failed: {e}")
        return {"display_name": f"{lat}, {lng}", "address": {}}

@router.get("/api/v1/alerts")
@limiter.limit("100/hour")
async def get_alerts(request: Request, response: Response = None):
    # Try real PostgreSQL analytics (cached server-side for 5 minutes)
    alerts = await analytics_service.get_hotspot_alerts()
    # Cache alerts for 5 minutes (matches server-side cache TTL)
    if response:
        response.headers["Cache-Control"] = "public, max-age=300, s-maxage=300"
    return alerts

# Report Ownership - Edit and Delete
@router.put("/api/v1/report/{report_id}")
@limiter.limit("50/hour")
async def update_report(
    request: Request,
    report_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Edit a report (title and description only).
    User must be authenticated and be the owner of the report.
    SECURITY: Username is extracted from JWT token to prevent IDOR attacks.
    Can only edit reports in PENDING_VERIFICATION, VERIFIED, or FLAGGED status.
    """
    username = current_user.get('username') or current_user.get('email')
    if not username:
        raise HTTPException(status_code=500, detail="User identity not found in token")

    # Get the report
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check ownership
    if report.get('submitted_by') != username:
        raise HTTPException(status_code=403, detail="You don't have permission to edit this report")

    # Check status - can't edit resolved/rejected/duplicate reports
    if report.get('status') in ['RESOLVED', 'REJECTED', 'DUPLICATE', 'IN_PROGRESS']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit report with status {report['status']}"
        )

    # Sanitize inputs
    sanitized = sanitize_form_data({
        "title": title,
        "description": description
    })

    updates = {}
    if sanitized.get("title"):
        updates["title"] = sanitized["title"]
    if sanitized.get("description"):
        updates["description"] = sanitized["description"]

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Update report
    await db_service.update_report(report_id, updates)

    # Add timeline event
    await db_service.add_timeline_event(
        report_id,
        "REPORT_EDITED",
        "User updated report details"
    )

    logger.info(f"Report {report_id} edited by {username}")  # Changed from user_email to username
    return {"message": "Report updated successfully", "report_id": report_id}

@router.delete("/api/v1/report/{report_id}")
@limiter.limit("50/hour")
async def delete_report(
    request: Request,
    report_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a report.
    User must be authenticated and be the owner of the report.
    SECURITY: Username is extracted from JWT token to prevent IDOR attacks.
    Can only delete reports in PENDING_VERIFICATION, FLAGGED, or REJECTED status.
    """
    username = current_user.get('username') or current_user.get('email')
    if not username:
        raise HTTPException(status_code=500, detail="User identity not found in token")

    # Get the report
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check ownership
    if report.get('submitted_by') != username:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this report")

    # Check status - can't delete verified/resolved/in_progress reports
    if report.get('status') in ['VERIFIED', 'RESOLVED', 'IN_PROGRESS', 'DUPLICATE']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete report with status {report['status']}. Contact admin for assistance."
        )

    # Delete report
    success = await db_service.delete_report_by_id(report_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete report")

    logger.info(f"Report {report_id} deleted by {username}")
    return {"message": "Report deleted successfully"}

@router.get("/api/v1/report/{report_id}/nearby-landmarks")
@limiter.limit("100/hour")
async def get_report_nearby_landmarks(
    request: Request,
    report_id: str
):
    """
    Get nearby landmarks for a report (within 500m radius).
    Returns up to 5 landmarks with distance information.
    Public endpoint - no authentication required.
    """
    # Get report
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check if report has coordinates
    latitude = report.get('latitude')
    longitude = report.get('longitude')

    if not latitude or not longitude:
        return {"landmarks": []}

    # Get nearby landmarks
    try:
        landmarks = await geo_service.get_multiple_nearby_landmarks(
            lat=latitude,
            lng=longitude,
            radius_m=500,
            limit=5
        )

        # Format for response
        formatted_landmarks = []
        for lm in landmarks:
            # Format distance text
            if lm['distance_m'] == 0:
                distance_text = "At location"
            elif lm['distance_m'] < 1000:
                distance_text = f"{lm['distance_m']}m away"
            else:
                distance_text = f"{lm['distance_m']/1000:.1f}km away"

            formatted_landmarks.append({
                "name": lm['name'],
                "type": lm['type'],
                "distance_m": lm['distance_m'],
                "distance_text": distance_text
            })

        return {"landmarks": formatted_landmarks}

    except Exception as e:
        logger.error(f"Failed to get nearby landmarks for report {report_id}: {e}")
        return {"landmarks": []}

# Report Updates
class ReportUpdateCreate(BaseModel):
    content: str
    status: str = 'public'
    media_urls: Optional[List[str]] = None
    is_official: bool = False

@router.post("/api/v1/reports/{report_id}/updates")
async def create_report_update_endpoint(
    report_id: str,
    update_data: ReportUpdateCreate,
    current_user: dict = Depends(get_current_user)
):
    role = current_user.get('role')
    # Allow admins, moderators, official users, and potentially verification agents
    if role not in ['super_admin', 'moderator', 'official', 'bot']:
         raise HTTPException(status_code=403, detail="Not authorized to post updates")
    
    return await db_service.create_report_update(
        report_id=report_id,
        author_id=current_user['id'],
        content=update_data.content,
        status=update_data.status,
        media_urls=update_data.media_urls,
        is_official=update_data.is_official
    )

@router.get("/api/v1/reports/{report_id}/updates")
async def get_report_updates_endpoint(
    report_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    include_internal = False
    if current_user:
        role = current_user.get('role')
        if role in ['super_admin', 'moderator', 'official', 'bot']:
            include_internal = True
            
    return await db_service.get_report_updates(report_id, include_internal)
