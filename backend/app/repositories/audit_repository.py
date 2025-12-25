"""
Audit Repository - Data access for AuditLog model
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.audit import AuditLog, AuditStatus

logger = structlog.get_logger()


class AuditRepository:
    """
    Repository for AuditLog model

    Encapsulates all database operations for AuditLog entity.
    Service layer uses this instead of direct database queries.
    """

    async def find_all(
        self,
        db: AsyncSession,
        action_type: str | None = None,
        status: str | None = None,
        resource_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """
        Find audit logs with filters and pagination

        Args:
            db: Database session
            action_type: Filter by action type
            status: Filter by status
            resource_id: Filter by resource ID
            limit: Page size
            offset: Pagination offset

        Returns:
            Tuple of (audit logs list, total count)
        """
        # Build query
        stmt = select(AuditLog)

        if action_type:
            stmt = stmt.where(AuditLog.action_type == action_type)

        if status:
            stmt = stmt.where(AuditLog.status == AuditStatus(status))

        if resource_id:
            stmt = stmt.where(AuditLog.resource_id == resource_id)

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        # Get paginated results
        stmt = stmt.order_by(AuditLog.executed_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total

    async def find_by_id(
        self,
        db: AsyncSession,
        log_id: int,
    ) -> AuditLog | None:
        """
        Find audit log by ID

        Args:
            db: Database session
            log_id: Audit log ID

        Returns:
            AuditLog object or None
        """
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_rollback_eligible(
        self,
        db: AsyncSession,
        retention_days: int = 7,
    ) -> list[AuditLog]:
        """
        Find actions eligible for rollback

        Args:
            db: Database session
            retention_days: Number of days to keep rollback option

        Returns:
            List of rollback-eligible audit logs
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        stmt = select(AuditLog).where(
            and_(
                AuditLog.can_rollback,
                AuditLog.status == AuditStatus.SUCCESS,
                AuditLog.rolled_back_at.is_(None),
                AuditLog.executed_at >= cutoff_date,
                ~AuditLog.dry_run,
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        audit_log: AuditLog,
    ) -> AuditLog:
        """
        Create audit log

        Args:
            db: Database session
            audit_log: AuditLog object to create

        Returns:
            Created AuditLog object
        """
        db.add(audit_log)
        await db.flush()
        await db.refresh(audit_log)

        logger.info(
            "Created audit log",
            log_id=audit_log.id,
            action_type=audit_log.action_type.value,
            resource_id=audit_log.resource_id,
        )

        return audit_log

    async def update(
        self,
        db: AsyncSession,
        audit_log: AuditLog,
    ) -> AuditLog:
        """
        Update audit log

        Args:
            db: Database session
            audit_log: AuditLog object to update

        Returns:
            Updated AuditLog object
        """
        await db.flush()
        await db.refresh(audit_log)
        return audit_log

    async def find_by_detection_id(
        self,
        db: AsyncSession,
        detection_id: int,
    ) -> list[AuditLog]:
        """
        Find audit logs by detection ID

        Args:
            db: Database session
            detection_id: Detection ID

        Returns:
            List of AuditLog objects
        """
        stmt = select(AuditLog).where(AuditLog.detection_id == detection_id)
        stmt = stmt.order_by(AuditLog.executed_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(
        self,
        db: AsyncSession,
        status: AuditStatus,
    ) -> int:
        """
        Count audit logs by status

        Args:
            db: Database session
            status: Action status

        Returns:
            Count of audit logs
        """
        stmt = (
            select(func.count()).select_from(AuditLog).where(AuditLog.status == status)
        )
        result = await db.execute(stmt)
        return result.scalar_one()


# Singleton instance
audit_repository = AuditRepository()
