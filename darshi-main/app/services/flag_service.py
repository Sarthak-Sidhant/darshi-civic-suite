"""
Flag Service - Handles report and update flagging with rate limiting.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.services import postgres_service as db
from app.services.audit_service import audit_service
from app.core.exceptions import RateLimitError, ValidationError

logger = logging.getLogger(__name__)


# Rate limits
MAX_FLAGS_PER_HOUR = 3
MAX_FLAGS_PER_DAY = 10


class FlagService:
    """Service for managing report and update flags."""
    
    FLAG_TYPES = ["fake_report", "inappropriate", "spam", "request_update", "other"]
    
    async def create_flag(
        self,
        report_id: str,
        user_id: str,
        flag_type: str,
        reason: Optional[str] = None,
        image_url: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a flag for a report.
        
        Args:
            report_id: UUID of the report to flag
            user_id: Username of the flagger
            flag_type: Type of flag (fake_report, inappropriate, spam, request_update, other)
            reason: Optional explanation
            image_url: Optional proof image URL
            ip_address: Client IP for audit
            
        Returns:
            Created flag data
            
        Raises:
            RateLimitError: If user has exceeded flag limits
            ValidationError: If flag_type is invalid
        """
        # Validate flag type
        if flag_type not in self.FLAG_TYPES:
            raise ValidationError(f"Invalid flag type. Must be one of: {self.FLAG_TYPES}")
        
        # Check rate limits
        await self._check_rate_limit(user_id)
        
        # Check if user already flagged this report
        existing = await db.get_user_flag_for_report(user_id, report_id)
        if existing:
            raise ValidationError("You have already flagged this report")
        
        # Create the flag
        flag = await db.create_report_flag(
            report_id=report_id,
            user_id=user_id,
            flag_type=flag_type,
            reason=reason,
            image_url=image_url
        )
        
        # Update rate limit counters
        await db.increment_flag_rate_limit(user_id)
        
        # Log to audit
        await audit_service.log_flag_created(
            flag_id=flag["id"],
            report_id=report_id,
            user_id=user_id,
            flag_type=flag_type,
            ip_address=ip_address
        )
        
        logger.info(f"Flag created: {flag['id']} on report {report_id} by {user_id}")
        return flag
    
    async def _check_rate_limit(self, user_id: str) -> None:
        """Check if user has exceeded flag rate limits."""
        limits = await db.get_flag_rate_limits(user_id)
        
        if not limits:
            return  # No limits record yet, allow
        
        # Reset hourly if needed
        hourly_reset = limits.get("hourly_reset_at")
        if hourly_reset and datetime.utcnow() - hourly_reset > timedelta(hours=1):
            await db.reset_flag_hourly_limit(user_id)
            limits["hourly_count"] = 0
        
        # Reset daily if needed
        daily_reset = limits.get("daily_reset_at")
        if daily_reset and daily_reset < datetime.utcnow().date():
            await db.reset_flag_daily_limit(user_id)
            limits["daily_count"] = 0
        
        # Check limits
        if limits.get("hourly_count", 0) >= MAX_FLAGS_PER_HOUR:
            raise RateLimitError("You can only submit 3 flags per hour. Please wait.")
        
        if limits.get("daily_count", 0) >= MAX_FLAGS_PER_DAY:
            raise RateLimitError("You can only submit 10 flags per day. Please wait until tomorrow.")
    
    async def get_pending_flags(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get pending flags for admin review."""
        return await db.get_pending_flags(limit=limit, offset=offset)
    
    async def review_flag(
        self,
        flag_id: str,
        reviewer_id: str,
        reviewer_role: str,
        status: str,
        admin_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Review a flag (admin action).
        
        Args:
            flag_id: UUID of the flag
            reviewer_id: Username of the reviewing admin
            reviewer_role: Role of the reviewer
            status: New status (reviewed, dismissed, actioned)
            admin_note: Optional note from admin
            
        Returns:
            Updated flag data
        """
        if status not in ["reviewed", "dismissed", "actioned"]:
            raise ValidationError("Status must be: reviewed, dismissed, or actioned")
        
        # Get the flag to find report_id for audit
        flag = await db.get_flag_by_id(flag_id)
        if not flag:
            raise ValidationError("Flag not found")
        
        # Update the flag
        updated = await db.update_flag_status(
            flag_id=flag_id,
            status=status,
            reviewed_by=reviewer_id,
            admin_note=admin_note
        )
        
        # Log to audit
        await audit_service.log_flag_reviewed(
            flag_id=flag_id,
            report_id=flag["report_id"],
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            status=status,
            admin_note=admin_note
        )
        
        logger.info(f"Flag {flag_id} reviewed by {reviewer_id}: {status}")
        return updated
    
    async def create_update_flag(
        self,
        update_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Flag an individual report update."""
        # Rate limit applies to all flags
        await self._check_rate_limit(user_id)
        
        flag = await db.create_update_flag(
            update_id=update_id,
            user_id=user_id,
            reason=reason
        )
        
        await db.increment_flag_rate_limit(user_id)
        
        await audit_service.log(
            action_type=audit_service.ACTION_UPDATE_FLAGGED,
            entity_type=audit_service.ENTITY_UPDATE,
            entity_id=update_id,
            actor_id=user_id,
            new_value={"flag_id": flag["id"], "reason": reason}
        )
        
        return flag
    
    async def get_flag_stats(self) -> Dict[str, Any]:
        """Get flag statistics for admin dashboard."""
        return await db.get_flag_stats()


# Singleton instance
flag_service = FlagService()
