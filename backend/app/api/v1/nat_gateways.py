"""
NAT Gateway Detection API Endpoints
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.nat_gateway_service import nat_gateway_service

logger = structlog.get_logger()

router = APIRouter()


@router.post("/scan")
async def scan_nat_gateways(
    account_id: str | None = Query(default=None, description="AWS Account ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan AWS NAT Gateways, persist inventory + metrics, and return idle candidates.

    Args:
        account_id: Optional AWS account ID for record-keeping

    Returns:
        Scan result with total gateways found and idle candidates
    """
    try:
        result = await nat_gateway_service.run_scan(db=db, account_id=account_id)
    except Exception as e:
        logger.exception("NAT Gateway scan failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"NAT Gateway scan failed: {e!s}",
        ) from e
    return result


@router.get("/")
async def list_nat_gateway_candidates(
    db: AsyncSession = Depends(get_db),
):
    """
    List NAT Gateways flagged as idle waste candidates from stored data.

    Returns:
        List of idle NAT Gateway candidates with reason and cost estimate
    """
    try:
        result = await nat_gateway_service.list_candidates(db=db)
    except Exception as e:
        logger.exception(
            "Failed to list NAT Gateway candidates", error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list NAT Gateway candidates: {e!s}",
        ) from e
    return result


@router.get("/{nat_gateway_id}")
async def get_nat_gateway_candidate(
    nat_gateway_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get details for a specific NAT Gateway.

    Args:
        nat_gateway_id: The NAT Gateway resource ID (e.g. nat-0a1b2c3d4e5f67890)

    Returns:
        NAT Gateway detail with idle status and metrics summary
    """

    def _raise_not_found() -> None:
        raise HTTPException(
            status_code=404,
            detail=f"NAT Gateway '{nat_gateway_id}' not found",
        )

    try:
        result = await nat_gateway_service.get_candidate(
            db=db, nat_gateway_id=nat_gateway_id
        )
        if result is None:
            _raise_not_found()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to get NAT Gateway",
            nat_gateway_id=nat_gateway_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get NAT Gateway: {e!s}",
        ) from e
    return result
