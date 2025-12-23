"""
Audit Service - Orchestrates audit log operations and rollback workflows
"""

from typing import Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, ActionStatus
from app.aws.client import AWSClientFactory
from app.safety.rollback import RollbackExecutor
from app.repositories.audit_repository import audit_repository
import structlog

logger = structlog.get_logger()


class AuditService:
    """
    Service for audit log operations and rollback
    
    Responsibilities:
    - Manage audit log queries
    - Orchestrate rollback workflow
    - Handle rollback eligibility checking
    """

    async def list_audit_logs(
        self,
        db: AsyncSession,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """
        List audit logs with filters and pagination
        
        Args:
            db: Database session
            action_type: Filter by action type
            status: Filter by status
            resource_id: Filter by resource ID
            limit: Page size
            offset: Pagination offset
            
        Returns:
            Paginated audit log results
        """
        # Delegate to repository
        logs, total = await audit_repository.find_all(
            db=db,
            action_type=action_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            offset=offset,
        )
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": [log.to_dict() for log in logs],
        }

    async def get_audit_log(
        self,
        db: AsyncSession,
        log_id: int,
    ) -> Optional[AuditLog]:
        """
        Get a specific audit log by ID
        
        Args:
            db: Database session
            log_id: Audit log ID
            
        Returns:
            AuditLog object or None
        """
        return await audit_repository.find_by_id(db, log_id)

    async def get_rollback_eligible(
        self,
        db: AsyncSession,
        retention_days: int = 7,
    ) -> Dict:
        """
        Get actions eligible for rollback (within retention period)
        
        Args:
            db: Database session
            retention_days: Number of days to keep rollback option
            
        Returns:
            List of rollback-eligible audit logs
        """
        logs = await audit_repository.find_rollback_eligible(db, retention_days)
        
        return {
            "eligible_count": len(logs),
            "logs": [log.to_dict() for log in logs],
        }

    async def rollback_action(
        self,
        db: AsyncSession,
        log_id: int,
        rolled_back_by: str,
        client_factory: Optional[AWSClientFactory] = None,
    ) -> Dict:
        """
        Rollback a previously executed action
        
        Args:
            db: Database session
            log_id: Audit log ID
            rolled_back_by: User who initiated rollback
            client_factory: Optional AWS client factory
            
        Returns:
            Rollback result
        """
        # Get and validate audit log
        log = await self.get_audit_log(db, log_id)
        if not log:
            raise ValueError(f"Audit log {log_id} not found")
        
        log_dict = log.to_dict()
        
        # Check if rollback is possible
        if client_factory is None:
            client_factory = AWSClientFactory()
        
        rollback_executor = RollbackExecutor(client_factory)
        
        if not rollback_executor.can_rollback(log_dict):
            raise ValueError(
                "Action cannot be rolled back (outside retention period, "
                "already rolled back, or not rollbackable)"
            )
        
        # Execute AWS rollback (external operation)
        rollback_result = rollback_executor.rollback_action(
            log_dict,
            rolled_back_by,
        )
        
        if not rollback_result.get("success"):
            raise ValueError(rollback_result.get("error", "Rollback failed"))
        
        # Update audit log
        # SQLAlchemy tracks these changes automatically
        log.status = ActionStatus.ROLLED_BACK
        log.rolled_back_at = datetime.now(timezone.utc)
        log.rolled_back_by = rolled_back_by
        log.result = {**log.result, "rollback": rollback_result}
        
        logger.info(
            "Action rolled back successfully",
            log_id=log_id,
            resource_id=log.resource_id,
            rolled_back_by=rolled_back_by,
        )
        
        # TRANSACTION COMMITS automatically in get_db() when function returns
        return {
            "audit_log": log.to_dict(),
            "rollback_result": rollback_result,
        }


# Singleton instance
audit_service = AuditService()

