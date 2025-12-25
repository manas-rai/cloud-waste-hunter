"""
Detection API Endpoints

This layer handles HTTP concerns only:
- Request/response formatting
- Input validation
- Error handling
- HTTP status codes

Business logic is delegated to the service layer.
"""

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.detection_models import DetectionPayload
from app.services.action_service import action_service
from app.services.detection_service import detection_service

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
        result = await detection_service.run_scan(
            db=db,
            resource_types=payload.resource_types,
        )
    except Exception as e:
        logger.exception("Scan failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Scan failed: {e!s}",
        ) from e
    return result


@router.get("/")
async def list_detections(
    status: str | None = None,
    resource_type: str | None = None,
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
    except Exception as e:
        logger.exception("List detections failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list detections: {e!s}",
        ) from e
    return result


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

    def _raise_not_found() -> None:
        raise HTTPException(status_code=404, detail="Detection not found")

    try:
        detection = await detection_service.get_detection(
            db=db, detection_id=detection_id
        )
        if not detection:
            _raise_not_found()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Get detection failed", detection_id=detection_id, error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get detection: {e!s}",
        ) from e
    return detection.to_dict()


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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(
            "Preview action failed", detection_id=detection_id, error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview action: {e!s}",
        ) from e
    return preview
