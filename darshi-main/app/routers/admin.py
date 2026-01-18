from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.services import postgres_service as db_service, auth_service, admin_service, notification_service
from app.services.audit_service import audit_service
from app.models.notification import NotificationType
from app.core.security import limiter, sanitize_form_data
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class StatusUpdateRequest(BaseModel):
    status: str # RESOLVED, REJECTED, IN_PROGRESS
    note: Optional[str] = None
    resolution_summary: Optional[str] = None
    resolution_image_url: Optional[str] = None

class CreateAdminRequest(BaseModel):
    email: str
    password: str
    role: str = "moderator"

class UpdateAdminStatusRequest(BaseModel):
    is_active: bool

async def get_current_admin(token: str = Header(..., alias="Authorization")):
    """
    Dependency to verify admin authentication.
    SECURITY: Only accepts tokens with user_type='admin'.
    Supports both OAuth-authenticated admins (users table) and legacy admins (admins collection).
    """
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication format")

    token = token.split(" ")[1]
    payload = auth_service.verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # SECURITY: Verify this is an admin token
    user_type = payload.get("user_type")
    if user_type != "admin":
        logger.warning(f"Non-admin token used for admin endpoint: user_type={user_type}")
        raise HTTPException(
            status_code=403,
            detail="Admin access denied. Citizen tokens cannot be used for admin endpoints."
        )

    # Get admin identifier from token
    admin_identifier = payload.get("sub") or payload.get("email") or payload.get("username")
    if not admin_identifier:
        raise HTTPException(status_code=401, detail="Invalid token format")

    # First, check users table for OAuth-authenticated admins
    user = await db_service.get_user_by_username(admin_identifier)
    
    # Check if user is active and has appropriate role
    if user and user.get('is_active', True):
        role = user.get('role')
        if role in ['admin', 'super_admin', 'municipality_admin', 'municipality_staff']:
            logger.debug(f"Admin authenticated: {admin_identifier} (Role: {role})")
            return {
                "email": user.get('email'),
                "username": user.get('username'),
                "role": role,
                "municipality_id": user.get('municipality_id'), # CRITICAL: Context
                "is_active": True
            }

    # Fallback to legacy admin collection (Super Admin equivalent)
    admin = admin_service.get_admin(admin_identifier)
    if admin and admin.get("is_active"):
        admin['role'] = 'super_admin' # Treat legacy as super
        return admin

    raise HTTPException(status_code=403, detail="Admin access denied or account inactive")

# Legacy admin login removed - admins now authenticate via OAuth (Google)
# If you need to add an admin, set role='admin' in the users table:
# UPDATE users SET role = 'admin' WHERE username = 'your_username';

@router.put("/api/v1/admin/report/{report_id}/status")
@limiter.limit("500/hour")  # Rate limit admin operations (increased for testing)
async def update_status(
    request: Request,
    report_id: str,
    update: StatusUpdateRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Update report status (admin only).
    Requires admin authentication via Bearer token.
    """
    # Sanitize input
    sanitized = sanitize_form_data({
        "status": update.status,
        "note": update.note,
        "resolution_summary": update.resolution_summary,
        "resolution_image_url": update.resolution_image_url
    })
    
    # Enforce resolution requirements
    if sanitized["status"] == "RESOLVED":
        if not sanitized.get("resolution_summary") and not sanitized.get("note"):
             raise HTTPException(status_code=400, detail="Resolution proof (summary or note) is required to resolve a report")

    updates = {"status": sanitized["status"]}
    if sanitized["note"]:
        updates["admin_note"] = sanitized["note"]
    
    if sanitized.get("resolution_summary"):
        updates["resolution_summary"] = sanitized.get("resolution_summary")
    if sanitized.get("resolution_image_url"):
        updates["resolution_image_url"] = sanitized.get("resolution_image_url")

    # Add timeline event with admin info
    await db_service.add_timeline_event(
        report_id,
        f"STATUS_CHANGED_{sanitized['status']}",
        sanitized["note"] or f"Status updated by {admin['email']}"
    )

    await db_service.update_report(report_id, updates)

    # Send notification to report author
    try:
        report = await db_service.get_report_by_id(report_id)
        if report and report.get('username'):
            report_title = report.get('title', 'Your report')
            status_display = sanitized['status'].replace('_', ' ').title()

            # Build notification message
            notification_title = f"Report Status: {status_display}"
            notification_message = f"Admin updated your report '{report_title}' to {status_display}."
            if sanitized.get('note'):
                notification_message += f" Note: {sanitized['note']}"

            # Create in-app notification
            notif_id = notification_service.create_notification(
                user_id=report['username'],
                notification_type=NotificationType.ADMIN_ACTION,
                title=notification_title,
                message=notification_message,
                report_id=report_id,
                actor=admin['email']
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
                logger.warning(f"Browser push failed for admin action on report {report_id}: {push_error}")

    except Exception as e:
        # Don't fail the whole operation if notification fails
        logger.warning(f"Failed to send admin action notification for report {report_id}: {e}")

    # Log audit trail
    await audit_service.log_action(
        action="UPDATE_REPORT_STATUS",
        user_id=admin['email'],
        resource_type="report",
        resource_id=report_id,
        details={
            "new_status": sanitized["status"],
            "note": sanitized["note"],
            "previous_status": None  # Could fetch from DB if needed
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )

    logger.info(f"Admin {admin['email']} updated report {report_id} status to {sanitized['status']}")

    return {
        "message": f"Report {report_id} updated to {sanitized['status']}",
        "updated_by": admin['email']
    }

@router.get("/api/v1/admin/admins")
@limiter.limit("500/hour")
async def list_admins(
    request: Request,
    admin: dict = Depends(get_current_admin)
):
    """
    List all admin users (super_admin only).
    """
    # Only super_admin can list admins
    if not admin_service.verify_admin_permission(admin['email'], required_role="super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")

    admins = admin_service.list_admins(include_inactive=True)
    return {"admins": admins}


@router.get("/api/v1/admin/analytics/dashboard")
@limiter.limit("500/hour")
async def get_admin_dashboard(
    request: Request,
    municipality_id: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """
    Get comprehensive analytics for admin dashboard.
    Returns report statistics, status distribution, recent activity, etc.
    
    CRITICAL: Super Admins should select a municipality context.
    Municipality Admins are forced to their context.
    """
    # ENFORCE CONTEXT
    if admin.get('role') in ['municipality_admin', 'municipality_staff']:
        # Force their own municipality
        municipality_id = admin.get('municipality_id')
        if not municipality_id:
             raise HTTPException(status_code=403, detail="Municipality official has no assigned municipality")
    
    # If Super Admin and no municipality_id, returns GLOBAL stats (allowed but UI should default to selector)

    try:
        # Get all reports for analytics (Filtered by municipality if set)
        if municipality_id:
             # TODO: Optimize: Creating a specialized DB call for this is better
             # For now, we fetch recent and filter in memory or add filter to get_reports
             # Using get_dashboard_stats from postgres_service which is optimized
             stats = await db_service.get_dashboard_stats(municipality_id=municipality_id)
             return {
                 "summary": stats,
                 "recent_admin_actions": [], # TODO: Filter audit logs by municipality context
                 "generated_at": datetime.utcnow().isoformat()
             }

        all_reports = await db_service.get_reports(limit=1000)

        # Calculate statistics
        total_reports = len(all_reports)
        status_counts = {}
        category_counts = {}
        severity_sum = 0
        severity_count = 0

        for report in all_reports:
            # Status distribution
            status = report.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1

            # Category distribution
            category = report.get('category', 'Uncategorized')
            category_counts[category] = category_counts.get(category, 0) + 1

            # Average severity
            try:
                severity = int(report.get('severity', 0) or 0)
            except (ValueError, TypeError):
                severity = 0

            if severity > 0:
                severity_sum += severity
                severity_count += 1

        avg_severity = round(severity_sum / severity_count, 2) if severity_count > 0 else 0

        # Get recent audit logs
        recent_actions = await audit_service.get_admin_actions(limit=50)

        # Performance metrics (top issues by category)
        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "summary": {
                "total_reports": total_reports,
                "average_severity": avg_severity,
                "status_distribution": status_counts,
                "category_distribution": category_counts,
            },
            "top_categories": [
                {"category": cat, "count": count}
                for cat, count in top_categories
            ],
            "recent_admin_actions": recent_actions[:20],
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to generate admin dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate dashboard analytics")


@router.get("/api/v1/admin/analytics/audit-logs")
@limiter.limit("500/hour")
async def get_audit_logs(
    request: Request,
    admin: dict = Depends(get_current_admin),
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """
    Get audit logs with optional filtering.
    Supports filtering by user_id, resource_type, resource_id, action.
    """
    logs = await audit_service.get_logs(
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        limit=limit
    )

    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action
        }
    }


@router.get("/api/v1/admin/analytics/user-activity/{user_id}")
@limiter.limit("100/hour")
async def get_user_activity(
    request: Request,
    user_id: str,
    admin: dict = Depends(get_current_admin),
    limit: int = 50
):
    """
    Get activity history for a specific user (admin or citizen).
    """
    activity = await audit_service.get_user_activity(user_id, limit=limit)

    return {
        "user_id": user_id,
        "activity": activity,
        "count": len(activity)
    }


@router.get("/api/v1/admin/analytics/report-history/{report_id}")
@limiter.limit("100/hour")
async def get_report_history(
    request: Request,
    report_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Get complete audit history for a specific report.
    Includes all status changes, admin actions, and timeline events.
    """
    # Get report details
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Get audit logs for this report
    audit_logs = await audit_service.get_resource_history("report", report_id, limit=100)

    return {
        "report_id": report_id,
        "current_status": report.get("status"),
        "timeline": report.get("timeline", []),
        "audit_logs": audit_logs,
        "created_at": report.get("created_at")
    }


@router.delete("/api/v1/admin/report/{report_id}")
@limiter.limit("100/hour")
async def delete_report_admin(
    request: Request,
    report_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Delete a report (admin only). Admins can delete any report regardless of status.
    Requires admin authentication via Bearer token.
    """
    # Check if report exists
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete the report
    success = await db_service.delete_report_by_id(report_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete report")

    # Log audit trail
    await audit_service.log_action(
        action="DELETE_REPORT",
        user_id=admin['email'],
        resource_type="report",
        resource_id=report_id,
        details={
            "previous_status": report.get("status"),
            "reason": "Admin deletion"
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )

    logger.info(f"Admin {admin['email']} deleted report {report_id}")

    return {
        "message": f"Report {report_id} deleted successfully",
        "deleted_by": admin['email']
    }


class CategoryUpdateRequest(BaseModel):
    category: str

@router.put("/api/v1/admin/report/{report_id}/category")
@limiter.limit("500/hour")
async def update_category(
    request: Request,
    report_id: str,
    update: CategoryUpdateRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Update report category (admin only).
    Requires admin authentication via Bearer token.
    """
    # Check if report exists
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Sanitize input
    sanitized_category = sanitize_form_data({"category": update.category})["category"]

    # Update category
    await db_service.update_report(report_id, {"category": sanitized_category})

    # Add timeline event
    await db_service.add_timeline_event(
        report_id,
        "CATEGORY_UPDATED",
        f"Category changed to {sanitized_category} by {admin['email']}"
    )

    # Log audit trail
    await audit_service.log_action(
        action="UPDATE_REPORT_CATEGORY",
        user_id=admin['email'],
        resource_type="report",
        resource_id=report_id,
        details={
            "new_category": sanitized_category,
            "previous_category": report.get("category")
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )

    logger.info(f"Admin {admin['email']} updated report {report_id} category to {sanitized_category}")

    return {
        "message": f"Report category updated to {sanitized_category}",
        "updated_by": admin['email']
    }


@router.delete("/api/v1/admin/report/{report_id}/comment/{comment_id}")
@limiter.limit("100/hour")
async def delete_comment(
    request: Request,
    report_id: str,
    comment_id: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Delete a comment from a report (admin only).
    Requires admin authentication via Bearer token.
    """
    # Check if report exists
    report = await db_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete the comment
    success = await db_service.delete_comment(report_id, comment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Log audit trail
    await audit_service.log_action(
        action="DELETE_COMMENT",
        user_id=admin['email'],
        resource_type="comment",
        resource_id=comment_id,
        details={
            "report_id": report_id,
            "reason": "Admin deletion"
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        status="success"
    )

    logger.info(f"Admin {admin['email']} deleted comment {comment_id} from report {report_id}")

    return {
        "message": f"Comment {comment_id} deleted successfully",
        "deleted_by": admin['email']
    }


@router.post("/api/v1/admin/create-admin")
@limiter.limit("10/hour")
async def create_new_admin(
    request: Request,
    data: CreateAdminRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Create a new admin user (super_admin only).
    """
    # Only super_admin can create admins
    if not admin_service.verify_admin_permission(admin['email'], required_role="super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")

    try:
        new_admin = admin_service.create_admin(
            email=data.email,
            password=data.password,
            role=data.role,
            created_by=admin['email']
        )

        # Log audit trail
        await audit_service.log_action(
            action="CREATE_ADMIN",
            user_id=admin['email'],
            resource_type="admin",
            resource_id=data.email,
            details={
                "new_admin_email": data.email,
                "role": data.role
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            status="success"
        )

        logger.info(f"Admin {admin['email']} created new admin: {data.email} with role {data.role}")

        return {
            "message": f"Admin {data.email} created successfully",
            "admin": new_admin
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create admin: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create admin")


@router.get("/api/v1/admin/reports")
@limiter.limit("100/hour")
async def get_admin_reports(
    request: Request,
    start_after_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    admin: dict = Depends(get_current_admin)
):
    """
    Get reports for admin view (includes REJECTED and FLAGGED).

    Query Parameters:
    - start_after_id: Pagination cursor
    - status: Filter by status (REJECTED, FLAGGED, VERIFIED, etc.)
    - limit: Number of reports to return (default 20, max 100)
    """
    # Enforce max limit
    limit = min(limit, 100)

    reports = await db_service.get_reports_admin(
        limit=limit,
        start_after_id=start_after_id,
        status_filter=status
    )

    return reports

@router.put("/api/v1/admin/manage/{admin_email}/status")
@limiter.limit("50/hour")
async def update_admin_status_endpoint(
    request: Request,
    admin_email: str,
    data: UpdateAdminStatusRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Activate or deactivate an admin account (super_admin only).
    """
    # Only super_admin can modify admin status
    if not admin_service.verify_admin_permission(admin['email'], required_role="super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")

    # Prevent deactivating yourself
    if admin_email == admin['email']:
        raise HTTPException(status_code=400, detail="Cannot modify your own status")

    try:
        admin_service.update_admin_status(
            email=admin_email,
            is_active=data.is_active,
            updated_by=admin['email']
        )

        # Log audit trail
        await audit_service.log_action(
            action="UPDATE_ADMIN_STATUS",
            user_id=admin['email'],
            resource_type="admin",
            resource_id=admin_email,
            details={
                "new_status": "active" if data.is_active else "inactive"
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            status="success"
        )

        logger.info(f"Admin {admin['email']} updated status of {admin_email} to {'active' if data.is_active else 'inactive'}")

        return {
            "message": f"Admin {admin_email} {'activated' if data.is_active else 'deactivated'} successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update admin status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update admin status")


# ============================================================================
# USER METADATA ENDPOINTS (Signup Location Tracking)
# ============================================================================

@router.get("/api/v1/admin/user/{username}/metadata")
@limiter.limit("100/hour")
async def get_user_metadata(
    request: Request,
    username: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Get user signup metadata (IP, location, VPN detection).
    Useful for verifying user authenticity.
    """
    # Get user to verify they exist
    user = await db_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get metadata
    metadata = await db_service.get_user_metadata(username)
    
    # Combine user info with metadata
    return {
        "username": username,
        "claimed_location": {
            "city": user.get("city"),
            "state": user.get("state"),
            "country": user.get("country")
        },
        "signup_metadata": metadata,
        "location_mismatch": metadata.get("location_mismatch") if metadata else None,
        "vpn_detected": metadata.get("vpn_detected") if metadata else None,
        "user_created_at": user.get("created_at")
    }


@router.get("/api/v1/admin/users/metadata")
@limiter.limit("50/hour")
async def get_all_users_metadata(
    request: Request,
    admin: dict = Depends(get_current_admin),
    mismatch_only: bool = False,
    limit: int = 50
):
    """
    Get users with their signup metadata.
    
    Query Parameters:
    - mismatch_only: If true, only return users with location mismatch (suspicious)
    - limit: Number of users to return (default 50, max 100)
    """
    limit = min(limit, 100)
    
    users = await db_service.get_users_with_metadata(
        limit=limit,
        mismatch_only=mismatch_only
    )
    
    return {
        "users": users,
        "count": len(users),
        "filters": {
            "mismatch_only": mismatch_only
        }
    }


# ============================================================================
# MUNICIPALITY MANAGEMENT
# ============================================================================

@router.get("/api/v1/admin/municipalities")
@limiter.limit("100/hour")
async def get_municipalities(
    request: Request,
    include_inactive: bool = False,
    admin: dict = Depends(get_current_admin)
):
    """Get all municipalities for assignment dropdown."""
    municipalities = await db_service.get_municipalities(include_inactive=include_inactive)
    return {"municipalities": municipalities}


@router.get("/api/v1/admin/departments")
@limiter.limit("100/hour")
async def get_departments(
    request: Request,
    municipality_id: Optional[str] = None,
    admin: dict = Depends(get_current_admin)
):
    """Get departments, optionally filtered by municipality."""
    departments = await db_service.get_departments(municipality_id=municipality_id)
    return {"departments": departments}


class AssignReportRequest(BaseModel):
    municipality_id: str
    department_id: Optional[str] = None
    resolution_eta: Optional[datetime] = None


@router.put("/api/v1/admin/report/{report_id}/assign")
@limiter.limit("100/hour")
async def assign_report(
    request: Request,
    report_id: str,
    assignment: AssignReportRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Assign a report to a municipality and optionally a department.
    
    Body:
    - municipality_id: ID of the municipality to assign to
    - department_id: Optional department within the municipality
    - resolution_eta: Optional expected resolution time
    """
    try:
        success = await db_service.assign_report_to_municipality(
            report_id=report_id,
            municipality_id=assignment.municipality_id,
            department_id=assignment.department_id,
            assigned_by=admin.get("username") or admin.get("email"),
            resolution_eta=assignment.resolution_eta
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Log the assignment
        await audit_service.log_admin_action(
            admin_id=admin.get("username") or admin.get("email"),
            action="assign_report",
            resource_type="report",
            resource_id=report_id,
            details={
                "municipality_id": assignment.municipality_id,
                "department_id": assignment.department_id
            }
        )
        
        logger.info(f"Report {report_id} assigned to municipality {assignment.municipality_id}")
        
        return {
            "success": True,
            "message": f"Report assigned to municipality",
            "assignment": {
                "municipality_id": assignment.municipality_id,
                "department_id": assignment.department_id
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to assign report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/admin/municipality/{municipality_id}/reports")
@limiter.limit("100/hour")
async def get_municipality_reports(
    request: Request,
    municipality_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(get_current_admin)
):
    """Get all reports assigned to a specific municipality."""
    reports = await db_service.get_reports_by_municipality(
        municipality_id=municipality_id,
        status_filter=status,
        limit=min(limit, 100),
        offset=offset
    )
    
    return {
        "reports": reports,
        "count": len(reports),
        "municipality_id": municipality_id
    }


class UpdateResolutionRequest(BaseModel):
    resolution_notes: Optional[str] = None
    resolution_eta: Optional[datetime] = None


@router.put("/api/v1/admin/report/{report_id}/resolution")
@limiter.limit("100/hour")
async def update_report_resolution(
    request: Request,
    report_id: str,
    update: UpdateResolutionRequest,
    admin: dict = Depends(get_current_admin)
):
    """Update resolution notes and ETA for a report."""
    try:
        success = await db_service.update_report_resolution(
            report_id=report_id,
            resolution_notes=update.resolution_notes,
            resolution_eta=update.resolution_eta
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "success": True,
            "message": "Resolution details updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update resolution for {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

