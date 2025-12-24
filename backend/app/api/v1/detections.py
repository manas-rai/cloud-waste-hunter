"""
Detection API Endpoints

This layer handles HTTP concerns only:
- Request/response formatting
- Input validation
- Error handling
- HTTP status codes

Business logic is delegated to the service layer.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.models.detection_models import DetectionPayload
from app.services.detection_service import detection_service
from app.services.action_service import action_service
import structlog

logger = structlog.get_logger()

router = APIRouter()


@router.post("/scan")
async def scan_resources(
    payload: DetectionPayload = Body(),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan AWS resources and detect waste

    Args:
        resource_types: List of resource types to scan (ec2, ebs, snapshot)
                       If None, scans all types

    Returns:
        Scan results with total detections and savings
    """
    try:
        resource_types = [resource_type.value for resource_type in payload.resource_types]
        result = await detection_service.run_scan(
            db=db,
            resource_types=resource_types,
        )
        return result
    except Exception as e:
        logger.error("Scan failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {str(e)}",
        )


@router.get("/")
async def list_detections(
    status: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List all detections with optional filters

    Args:
        status: Filter by status
        resource_type: Filter by resource type
        limit: Page size (max 100)
        offset: Pagination offset

    Returns:
        Paginated list of detections
    """
    try:
        result = await detection_service.list_detections(
            db=db,
            status=status,
            resource_type=resource_type,
            limit=limit,
            offset=offset,
        )
        return result
    except Exception as e:
        logger.error("List detections failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list detections: {str(e)}",
        )


@router.get("/{detection_id}")
async def get_detection(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific detection

    Args:
        detection_id: Detection ID

    Returns:
        Detection details
    """
    try:
        detection = await detection_service.get_detection(db=db, detection_id=detection_id)
        if not detection:
            raise HTTPException(status_code=404, detail="Detection not found")
        return detection.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get detection failed", detection_id=detection_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detection: {str(e)}",
        )


@router.post("/{detection_id}/preview")
async def preview_action(
    detection_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Preview action for a detection (dry-run)

    Args:
        detection_id: Detection ID

    Returns:
        Action preview with impact analysis
    """
    try:
        preview = await action_service.preview_action(db=db, detection_id=detection_id)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Preview action failed", detection_id=detection_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview action: {str(e)}",
        )
