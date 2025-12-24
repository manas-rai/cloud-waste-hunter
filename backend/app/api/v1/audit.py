"""
Audit Log API Endpoints

This layer handles HTTP concerns only:
- Request/response formatting
- Input validation
- Error handling
- HTTP status codes

Business logic is delegated to the service layer.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.schemas.base import get_db
from app.models.audit_models import RollbackRequest
from app.services.audit_service import audit_service
from app.core.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    action_type: Optional[str] = None,
    status: Optional[str] = None,
    resource_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs with optional filters

    Args:
        action_type: Filter by action type
        status: Filter by status
        resource_id: Filter by resource ID
        limit: Page size (max 100)
        offset: Pagination offset

    Returns:
        Paginated list of audit logs
    """
    try:
        result = await audit_service.list_audit_logs(
            db=db,
            action_type=action_type,
            status=status,
            resource_id=resource_id,
            limit=limit,
            offset=offset,
        )
        return result
    except Exception as e:
        logger.error("List audit logs failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list audit logs: {str(e)}",
        )


@router.get("/{log_id}")
async def get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific audit log

    Args:
        log_id: Audit log ID

    Returns:
        Audit log details
    """
    try:
        log = await audit_service.get_audit_log(db=db, log_id=log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")
        return log.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get audit log failed", log_id=log_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit log: {str(e)}",
        )


@router.get("/rollback/eligible")
async def get_rollback_eligible(
    db: AsyncSession = Depends(get_db),
):
    """
    Get actions eligible for rollback (within retention period)

    Returns:
        List of rollback-eligible audit logs
    """
    try:
        result = await audit_service.get_rollback_eligible(
            db=db,
            retention_days=settings.ROLLBACK_RETENTION_DAYS,
        )
        return result
    except Exception as e:
        logger.error("Get rollback eligible failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get rollback eligible actions: {str(e)}",
        )


@router.post("/{log_id}/rollback")
async def rollback_action(
    log_id: int,
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Rollback a previously executed action

    Args:
        log_id: Audit log ID
        request: Rollback request with rolled_back_by

    Returns:
        Rollback result with updated audit log
    """
    try:
        result = await audit_service.rollback_action(
            db=db,
            log_id=log_id,
            rolled_back_by=request.rolled_back_by,
        )
        return result
    except ValueError as e:
        # Business logic errors (not found, cannot rollback, etc.)
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(
            "Rollback action failed",
            log_id=log_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to rollback action: {str(e)}",
        )
