"""
Action API Request/Response Schemas

Pydantic models for action-related API endpoints:
- Approval requests
- Batch operations
- Action execution
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """Request model for approving a detection"""

    approved_by: str = Field(
        ..., description="Email or ID of user approving the action"
    )
    dry_run: bool = Field(
        default=False, description="If True, simulate the action without executing"
    )


class BatchApprovalRequest(BaseModel):
    """Request model for batch approval"""

    detection_ids: list[int] = Field(
        ..., description="List of detection IDs to approve"
    )
    approved_by: str = Field(
        ..., description="Email or ID of user approving the actions"
    )
    dry_run: bool = Field(
        default=False, description="If True, simulate actions without executing"
    )


class BatchRejectRequest(BaseModel):
    """Request model for batch rejection"""

    detection_ids: list[int] = Field(..., description="List of detection IDs to reject")
    approved_by: str = Field(
        default="user@example.com", description="Email or ID of user rejecting"
    )


class ApprovalResponse(BaseModel):
    """Response model for approval/execution"""

    detection: dict[str, Any] = Field(..., description="Updated detection object")
    action_result: dict[str, Any] = Field(
        ..., description="Result of the action execution"
    )
    audit_log: dict[str, Any] = Field(..., description="Created audit log entry")

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "detection": {
                    "id": 1,
                    "resource_id": "i-1234567890abcdef0",
                    "status": "executed",
                },
                "action_result": {
                    "action_type": "stop_ec2_instance",
                    "success": True,
                },
                "audit_log": {
                    "id": 1,
                    "action_type": "stop_ec2_instance",
                    "status": "SUCCESS",
                },
            }
        }


class BatchOperationResult(BaseModel):
    """Result for a single operation in a batch"""

    detection_id: int
    success: bool
    result: dict[str, Any] | None = None
    detection: dict[str, Any] | None = None
    error: str | None = None


class BatchOperationResponse(BaseModel):
    """Response model for batch operations"""

    total: int = Field(..., description="Total number of operations")
    success: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: list[BatchOperationResult] = Field(
        ..., description="Individual operation results"
    )

    class Config:
        json_schema_extra: ClassVar[dict[str, Any]] = {
            "example": {
                "total": 5,
                "success": 4,
                "failed": 1,
                "results": [
                    {
                        "detection_id": 1,
                        "success": True,
                        "result": {"status": "executed"},
                    },
                    {
                        "detection_id": 2,
                        "success": False,
                        "error": "Resource not found",
                    },
                ],
            }
        }
