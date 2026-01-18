from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.models.user import UserProfileResponse, UserUpdateProfile, UserUpdateSettings
from app.services import postgres_service as db_service, storage_service
from app.routers.auth import get_current_user
from app.core.logging_config import get_logger
from app.core.validation import validate_city, validate_state, validate_country
from app.core.exceptions import InvalidInputError

logger = get_logger(__name__)
router = APIRouter()

@router.get("/api/v1/users/me/profile", response_model=UserProfileResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get complete profile of current user including stats"""
    return UserProfileResponse(**current_user)

@router.put("/api/v1/users/me/profile")
async def update_my_profile(profile: UserUpdateProfile, current_user: dict = Depends(get_current_user)):
    """Update user profile (username, name, location, picture URL)"""
    updates = {}

    # Use email as identifier (always present for OAuth users, username may be None)
    user_identifier = current_user.get('email') or current_user.get('username')
    if not user_identifier:
        raise HTTPException(status_code=400, detail="User identifier not found")

    # Check if username is being changed/set
    if profile.username is not None:
        current_username = current_user.get('username')
        if profile.username != current_username:
            # Validate username availability
            existing = await db_service.get_user_by_username(profile.username)
            if existing and existing.get('email') != current_user.get('email'):
                raise HTTPException(status_code=400, detail="Username already taken")
            updates['username'] = profile.username

    if profile.full_name is not None:
        updates['full_name'] = profile.full_name

    # Validate and sanitize location fields
    if profile.city is not None:
        try:
            validate_city(profile.city)
            updates['city'] = profile.city.strip()
        except InvalidInputError as e:
            raise HTTPException(status_code=400, detail=e.message)

    if profile.state is not None:
        try:
            validate_state(profile.state)
            updates['state'] = profile.state.strip()
        except InvalidInputError as e:
            raise HTTPException(status_code=400, detail=e.message)

    if profile.country is not None:
        try:
            validate_country(profile.country)
            updates['country'] = profile.country.strip()
        except InvalidInputError as e:
            raise HTTPException(status_code=400, detail=e.message)

    if profile.lat is not None:
        updates['lat'] = profile.lat
    if profile.lng is not None:
        updates['lng'] = profile.lng
    if profile.location_address is not None:
        # Sanitize location address (trim whitespace)
        location_addr = profile.location_address.strip() if profile.location_address else None
        if location_addr:
            updates['location_address'] = location_addr
    if profile.profile_picture is not None:
        updates['profile_picture'] = profile.profile_picture

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    success = await db_service.update_user_by_email(current_user['email'], updates)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    # Return updated user
    updated_user = await db_service.get_user_by_email(current_user['email'])
    return UserProfileResponse(**updated_user)

@router.post("/api/v1/users/me/profile-picture")
async def upload_profile_picture(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload profile picture to cloud storage.
    Returns the public URL of the uploaded image.
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read file
    contents = await file.read()

    # Upload to storage
    filename = f"profile_pictures/{current_user['email']}/{file.filename}"
    url = storage_service.upload_file(contents, filename, file.content_type)

    if not url:
        raise HTTPException(status_code=500, detail="Failed to upload image")

    # Update user profile
    await db_service.update_user(current_user['email'], {'profile_picture': url})

    return {"url": url, "message": "Profile picture uploaded successfully"}

@router.put("/api/v1/users/me/settings")
async def update_my_settings(settings: UserUpdateSettings, current_user: dict = Depends(get_current_user)):
    """Update user preferences/settings"""
    updates = {}

    if settings.notification_enabled is not None:
        updates['notification_enabled'] = settings.notification_enabled
    if settings.location_tracking_enabled is not None:
        updates['location_tracking_enabled'] = settings.location_tracking_enabled
    if settings.public_profile is not None:
        updates['public_profile'] = settings.public_profile

    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    success = await db_service.update_user(current_user['email'], updates)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update settings")

    return {"message": "Settings updated successfully"}

@router.get("/api/v1/users/me/reports")
async def get_my_reports(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get all reports submitted by current user"""
    reports = await db_service.get_user_reports(current_user['username'], limit=limit)
    return {"reports": reports, "total": len(reports)}

@router.get("/api/v1/users/me/stats")
async def get_my_stats(current_user: dict = Depends(get_current_user)):
    """Get user statistics using efficient SQL aggregation"""
    stats = await db_service.get_user_stats_aggregated(current_user['username'])

    return {
        **stats,
        "email_verified": current_user.get('email_verified', False),
        "phone_verified": current_user.get('phone_verified', False),
        "member_since": current_user.get('created_at')
    }

@router.delete("/api/v1/users/me/account")
async def delete_my_account(current_user: dict = Depends(get_current_user)):
    """
    Delete user account and all associated data.
    WARNING: This action is irreversible!
    """
    try:
        username = current_user['username']

        # Delete user account (CASCADE will delete related records)
        success = await db_service.delete_user(username)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete account")

        logger.info(f"User account deleted: {username}")
        return {"message": "Account deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete account")
