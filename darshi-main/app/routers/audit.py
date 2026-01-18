"""
Audit Router - API endpoints for viewing audit logs.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from app.services.auth import check_is_admin, check_is_moderator
from app.services.audit_service import audit_service

router = APIRouter()


@router.get("/admin/audit-logs")
async def get_audit_logs(
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: dict = Depends(check_is_moderator)
):
    """
    Query audit logs with filters (Admin/Mod only).
    """
    return await audit_service.query_logs(
        action_type=action_type,
        entity_type=entity_type,
        actor_id=actor_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )


@router.get("/reports/{report_id}/audit")
async def get_report_audit_trail(
    report_id: str,
    limit: int = Query(20, le=50)
):
    """
    Get public audit trail for a report (timeline).
    Sanitized for public viewing (filtered in frontend or service if needed).
    For now returning full technical logs, frontend should display nicely.
    """
    logs = await audit_service.get_entity_audit_trail(
        entity_type="report",
        entity_id=report_id,
        limit=limit
    )
    return logs
