"""
Action API Endpoints (Approve/Execute)

This layer handles HTTP concerns only:
- Request/response formatting
- Input validation
- Error handling
- HTTP status codes

Business logic is delegated to the service layer.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.base import get_db
from app.services.action_service import action_service
from app.models.action_models import (
    ApprovalRequest,
    BatchApprovalRequest,
    BatchRejectRequest,
)
import structlog

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# BATCH ROUTES (must come BEFORE parameterized routes)
# =============================================================================

@router.post("/batch/preview")
async def preview_batch_actions(
    request: BatchApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Preview batch actions

    Args:
        request: Batch approval request with detection IDs

    Returns:
        Batch preview with total impact
    """
    try:
        preview = await action_service.preview_batch_actions(
            db=db,
            detection_ids=request.detection_ids,
        )
        return preview
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Preview batch actions failed",
            detection_ids=request.detection_ids,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview batch actions: {str(e)}",
        )


@router.post("/batch/approve")
async def approve_batch_actions(
    request: BatchApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve and execute multiple actions at once

    Args:
        request: Batch approval request with detection IDs, approved_by, and dry_run flag

    Returns:
        Results for each action (success/failure)
    """
    try:
        results = []
        for detection_id in request.detection_ids:
            try:
                result = await action_service.approve_and_execute(
                    db=db,
                    detection_id=detection_id,
                    approved_by=request.approved_by,
                    dry_run=request.dry_run,
                )
                results.append({
                    "detection_id": detection_id,
                    "success": True,
                    "result": result,
                })
            except Exception as e:
                logger.error(
                    "Batch approve failed for detection",
                    detection_id=detection_id,
                    error=str(e),
                )
                results.append({
                    "detection_id": detection_id,
                    "success": False,
                    "error": str(e),
                })
        
        # Summary
        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count
        
        return {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "results": results,
        }
    except Exception as e:
        logger.error(
            "Batch approve failed",
            detection_ids=request.detection_ids,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve batch actions: {str(e)}",
        )


@router.post("/batch/reject")
async def reject_batch_detections(
    request: BatchRejectRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reject multiple detections at once

    Args:
        request: Batch rejection request with detection IDs and approved_by

    Returns:
        Results for each rejection (success/failure)
    """
    try:
        results = []
        for detection_id in request.detection_ids:
            try:
                detection = await action_service.reject_detection(
                    db=db,
                    detection_id=detection_id,
                    approved_by=request.approved_by,
                )
                results.append({
                    "detection_id": detection_id,
                    "success": True,
                    "detection": detection.to_dict(),
                })
            except Exception as e:
                logger.error(
                    "Batch reject failed for detection",
                    detection_id=detection_id,
                    error=str(e),
                )
                results.append({
                    "detection_id": detection_id,
                    "success": False,
                    "error": str(e),
                })
        
        # Summary
        success_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - success_count
        
        return {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "results": results,
        }
    except Exception as e:
        logger.error(
            "Batch reject failed",
            detection_ids=request.detection_ids,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject batch detections: {str(e)}",
        )


# =============================================================================
# SINGLE DETECTION ROUTES (parameterized - must come AFTER specific routes)
# =============================================================================

@router.post("/{detection_id}/approve")
async def approve_detection(
    detection_id: int,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve and execute action for a detection

    Args:
        detection_id: Detection ID
        request: Approval request with approved_by and dry_run flag

    Returns:
        Execution result with detection, action result, and audit log
    """
    try:
        result = await action_service.approve_and_execute(
            db=db,
            detection_id=detection_id,
            approved_by=request.approved_by,
            dry_run=request.dry_run,
        )
        return result
    except ValueError as e:
        # Business logic errors (not found, invalid status, etc.)
        status_code = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(
            "Approve detection failed",
            detection_id=detection_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve detection: {str(e)}",
        )


@router.post("/{detection_id}/reject")
async def reject_detection(
    detection_id: int,
    approved_by: str = "system",
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a detection (mark as not actionable)

    Args:
        detection_id: Detection ID
        approved_by: User who rejected (defaults to "system")

    Returns:
        Updated detection
    """
    try:
        detection = await action_service.reject_detection(
            db=db,
            detection_id=detection_id,
            approved_by=approved_by,
        )
        return detection.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Reject detection failed",
            detection_id=detection_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject detection: {str(e)}",
        )
