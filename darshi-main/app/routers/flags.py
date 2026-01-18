"""
Flag Router - API endpoints for report flags and moderation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.services.auth import get_current_user, check_is_admin, check_is_moderator
from app.services.flag_service import flag_service
from app.core.exceptions import RateLimitError, ValidationError

router = APIRouter()


class FlagCreate(BaseModel):
    flag_type: str
    reason: Optional[str] = None
    image_url: Optional[str] = None


class FlagReview(BaseModel):
    status: str
    admin_note: Optional[str] = None


@router.post("/reports/{report_id}/flag")
async def flag_report(
    report_id: str,
    flag_data: FlagCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Flag a report as fake, inappropriate, etc.
    Rate limited: 3/hour, 10/day per user.
    """
    try:
        flag = await flag_service.create_flag(
            report_id=report_id,
            user_id=current_user["username"],
            flag_type=flag_data.flag_type,
            reason=flag_data.reason,
            image_url=flag_data.image_url
        )
        return {"message": "Flag submitted successfully", "flag_id": flag["id"]}
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/updates/{update_id}/flag")
async def flag_update(
    update_id: str,
    reason: Optional[str] = Body(None, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """Flag a report update."""
    try:
        flag = await flag_service.create_update_flag(
            update_id=update_id,
            user_id=current_user["username"],
            reason=reason
        )
        return {"message": "Update flagged successfully", "flag_id": flag["id"]}
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/flags")
async def get_pending_flags(
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_user: dict = Depends(check_is_moderator)
):
    """Get pending flags for moderation (Admin/Mod only)."""
    return await flag_service.get_pending_flags(limit=limit, offset=offset)


@router.put("/admin/flags/{flag_id}")
async def review_flag(
    flag_id: str,
    review_data: FlagReview,
    current_user: dict = Depends(check_is_moderator)
):
    """Review and action a flag (Admin/Mod only)."""
    try:
        updated = await flag_service.review_flag(
            flag_id=flag_id,
            reviewer_id=current_user["username"],
            reviewer_role=current_user.get("role", "moderator"),
            status=review_data.status,
            admin_note=review_data.admin_note
        )
        return updated
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/flags/stats")
async def get_flag_stats(
    current_user: dict = Depends(check_is_moderator)
):
    """Get statistics about flags (Admin/Mod only)."""
    return await flag_service.get_flag_stats()
