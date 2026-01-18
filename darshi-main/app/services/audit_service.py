"""
Audit logging service for tracking admin actions and system events.
Stores audit logs in PostgreSQL for compliance and security monitoring.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.services import postgres_service as db
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for managing audit logs"""
    
    # Action type constants
    ACTION_FLAG_CREATED = "flag_created"
    ACTION_FLAG_REVIEWED = "flag_reviewed"
    ACTION_FLAG_DISMISSED = "flag_dismissed"
    ACTION_FLAG_ACTIONED = "flag_actioned"
    
    ACTION_REPORT_STATUS_CHANGED = "report_status_changed"
    ACTION_REPORT_ASSIGNED = "report_assigned"
    ACTION_REPORT_MERGED = "report_merged"
    
    ACTION_USER_ROLE_CHANGED = "user_role_changed"
    ACTION_USER_VERIFIED = "user_verified"
    ACTION_USER_WARNED = "user_warned"
    ACTION_USER_BANNED = "user_banned"
    
    ACTION_MUNICIPALITY_ASSIGNED = "municipality_assigned"
    ACTION_DEPARTMENT_CHANGED = "department_changed"
    
    ACTION_UPDATE_CREATED = "update_created"
    ACTION_UPDATE_DELETED = "update_deleted"
    ACTION_UPDATE_FLAGGED = "update_flagged"
    
    # Entity type constants
    ENTITY_REPORT = "report"
    ENTITY_USER = "user"
    ENTITY_FLAG = "flag"
    ENTITY_UPDATE = "update"
    ENTITY_MUNICIPALITY = "municipality"

    async def log(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ) -> Optional[str]:
        """Create an audit log entry."""
        try:
            return await db.create_audit_log(
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                actor_role=actor_role,
                old_value=old_value,
                new_value=new_value,
                metadata=metadata or {},
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def log_action(
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success"
    ) -> str:
        """Legacy log method for backward compatibility."""
        try:
            result = await db.create_audit_log(
                action_type=action,
                entity_type=resource_type,
                entity_id=resource_id or "",
                actor_id=user_id,
                new_value=details,
                ip_address=ip_address,
                metadata={"user_agent": user_agent, "status": status}
            )
            return result or ""
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}", exc_info=True)
            return ""
    
    async def log_flag_created(
        self,
        flag_id: str,
        report_id: str,
        user_id: str,
        flag_type: str,
        ip_address: Optional[str] = None
    ) -> Optional[str]:
        """Log when a user flags a report."""
        return await self.log(
            action_type=self.ACTION_FLAG_CREATED,
            entity_type=self.ENTITY_REPORT,
            entity_id=report_id,
            actor_id=user_id,
            new_value={"flag_id": flag_id, "flag_type": flag_type},
            ip_address=ip_address
        )
    
    async def log_flag_reviewed(
        self,
        flag_id: str,
        report_id: str,
        reviewer_id: str,
        reviewer_role: str,
        status: str,
        admin_note: Optional[str] = None
    ) -> Optional[str]:
        """Log when an admin reviews a flag."""
        action = self.ACTION_FLAG_DISMISSED if status == "dismissed" else self.ACTION_FLAG_ACTIONED
        return await self.log(
            action_type=action,
            entity_type=self.ENTITY_FLAG,
            entity_id=flag_id,
            actor_id=reviewer_id,
            actor_role=reviewer_role,
            old_value={"status": "pending"},
            new_value={"status": status, "admin_note": admin_note},
            metadata={"report_id": report_id}
        )
    
    async def log_status_change(
        self,
        report_id: str,
        old_status: str,
        new_status: str,
        actor_id: str,
        actor_role: str,
        note: Optional[str] = None
    ) -> Optional[str]:
        """Log when a report status changes."""
        return await self.log(
            action_type=self.ACTION_REPORT_STATUS_CHANGED,
            entity_type=self.ENTITY_REPORT,
            entity_id=report_id,
            actor_id=actor_id,
            actor_role=actor_role,
            old_value={"status": old_status},
            new_value={"status": new_status},
            metadata={"note": note} if note else None
        )
    
    async def log_report_assigned(
        self,
        report_id: str,
        municipality_id: Optional[str],
        department_id: Optional[str],
        actor_id: str,
        actor_role: str
    ) -> Optional[str]:
        """Log when a report is assigned."""
        return await self.log(
            action_type=self.ACTION_REPORT_ASSIGNED,
            entity_type=self.ENTITY_REPORT,
            entity_id=report_id,
            actor_id=actor_id,
            actor_role=actor_role,
            new_value={"municipality_id": municipality_id, "department_id": department_id}
        )
    
    async def get_entity_audit_trail(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a specific entity."""
        try:
            return await db.get_audit_logs_for_entity(entity_type, entity_id, limit)
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}", exc_info=True)
            return []
    
    async def get_admin_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent admin actions."""
        try:
            result = await db.query_audit_logs(limit=limit)
            return result.get("logs", [])
        except Exception:
            return []
    
    async def get_logs(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get filtered audit logs."""
        try:
            result = await db.query_audit_logs(
                actor_id=user_id,
                entity_type=resource_type,
                action_type=action,
                limit=limit
            )
            return result.get("logs", [])
        except Exception:
            return []
    
    async def get_user_activity(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get activity for a specific user."""
        return await self.get_logs(user_id=user_id, limit=limit)
    
    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get history for a specific resource."""
        return await self.get_entity_audit_trail(resource_type, resource_id, limit)


# Export instance
audit_service = AuditService()
